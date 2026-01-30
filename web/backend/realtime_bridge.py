"""
Realtime Bridge - Connects to OpenAI Realtime API on behalf of web clients
Handles the WebSocket connection and event processing
"""

import os
import json
import base64
import asyncio
import websockets
import ssl
import certifi
from datetime import datetime
from typing import Optional
import sys

# Add paths to import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core import AssessmentAgent, AssessmentStateMachine, AssessmentState
from core.tools.interview_guidance import get_interview_guidance


class RealtimeBridge:
    """Bridges web client to OpenAI Realtime API"""
    
    def __init__(self, session, client_websocket):
        """
        Initialize bridge
        
        Args:
            session: UserSession instance
            client_websocket: WebSocket connection to browser client
        """
        self.session = session
        self.client_ws = client_websocket
        self.openai_ws = None
        self.assessment_agent = AssessmentAgent()
        
        # Initialize assessment state machine
        self.session.assessment_state = AssessmentStateMachine()
        
        # Response tracking
        self.current_response_id = None
        self.response_in_progress = False  # Track if AI is currently responding
        
        # Track background tasks for cleanup
        self.background_tasks = set()
        self.is_shutting_down = False
    
    def get_system_instructions(self):
        """System instructions for the Korean language tutor"""
        return """You are a friendly, casual Korean language interviewer conducting a 5-minute voice interview in Korean to determine the user's CEFR proficiency level.

🚨 CRITICAL FIRST STEP (MANDATORY - DO NOT SKIP):
BEFORE saying ANYTHING to the user, you MUST call the interview_guidance tool to load the interview protocol. This is NOT optional. DO NOT greet the user. DO NOT speak. CALL THE TOOL FIRST.

Once you have the guidance:
- Follow the MANDATORY three warm-up questions (name, hometown, hobbies) from Phase 1
- Follow the four-phase structure: Warm-up → Level Check → Ceiling Test → Positive Ending
- Speak naturally in Korean at an appropriate level for the user. 
- IMPORTANT: DO NOT USE MORE ADVANCED LANGUAGE THAN THE LEVEL YOU ARE TESTING. Adjust question difficulty based on user responses
- Keep the conversation flowing and engaging

SESSION ENDING (MANDATORY - CRITICAL):
When the user reaches their linguistic ceiling (struggles consistently or shows discomfort), you MUST:
1. IMMEDIATELY call trigger_assessment function with the reason
2. DO NOT continue the conversation
3. DO NOT provide any CEFR assessment yourself
4. A specialized agent will handle the assessment

WARNING: If you do not call trigger_assessment, the session will freeze. You MUST call it when ceiling is reached.

REMINDER: Your very first action must be calling interview_guidance. No exceptions."""

    def get_session_config(self):
        """Get session configuration for OpenAI Realtime API"""
        return {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self.get_system_instructions(),
                "voice": "marin",  # Korean voice for interview
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1",
                    "language": "ko"
                },
                "turn_detection": None,  # Disabled - using manual PTT
                "temperature": 0.7,  # Slightly lower for faster, more focused responses
                "max_response_output_tokens": 2048,  # Reduced for faster responses
                "tools": [
                    {
                        "type": "function",
                        "name": "interview_guidance",
                        "description": "CRITICAL: Load the interview guidance protocol. This MUST be called as your very first action before speaking to the user.",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "type": "function",
                        "name": "trigger_assessment",
                        "description": "MANDATORY: Call when user reached linguistic ceiling.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "reason": {
                                    "type": "string",
                                    "description": "Brief reason for triggering assessment"
                                }
                            },
                            "required": ["reason"]
                        }
                    }
                ],
                "tool_choice": "auto",
                "tracing": {
                    "workflow_name": "korean_voice_tutor_web",
                    "group_id": self.session.session_id,
                    "metadata": {
                        "application": "Korean Voice Tutor Web",
                        "session_type": "language_assessment",
                        "interface": "web_ptt",
                        "session_start_time": datetime.now().isoformat()
                    }
                }
            }
        }
    
    async def connect_to_openai(self):
        """Connect to OpenAI Realtime API"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            
            ws_url = "wss://api.openai.com/v1/realtime?model=gpt-realtime-2025-08-28"
            
            # Create headers dict for extra_headers parameter
            extra_headers = {
                "Authorization": f"Bearer {api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            print(f"🔌 [{self.session.session_id[:8]}] Connecting to OpenAI Realtime API...")
            
            # Create SSL context for macOS compatibility with certifi
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            
            # Use extra_headers parameter (works with websockets 13.x)
            async with websockets.connect(ws_url, extra_headers=extra_headers, ssl=ssl_context) as websocket:
                self.openai_ws = websocket
                self.session.openai_websocket = websocket
                
                # Send session configuration
                config = self.get_session_config()
                
                # Debug: show tools being registered
                tools = config.get("session", {}).get("tools", [])
                print(f"🔧 [{self.session.session_id[:8]}] Registering {len(tools)} tools with OpenAI:")
                for tool in tools:
                    print(f"   📎 {tool.get('name', 'unknown')}: {tool.get('description', '')[:60]}...")
                
                print(f"📤 [{self.session.session_id[:8]}] Sending session config...")
                await websocket.send(json.dumps(config))
                print(f"✅ [{self.session.session_id[:8]}] Connected to OpenAI, config sent")
                
                # Send session info to client
                await self.send_to_client({
                    "type": "session_started",
                    "session_id": self.session.session_id,
                    "message": "Ready to start interview"
                })
                
                # CRITICAL: Trigger initial response to force tool call
                # Without this, AI never calls interview_guidance in PTT mode
                print(f"🔧 [{self.session.session_id[:8]}] Triggering initial response to load guidance...")
                self.response_in_progress = True
                await websocket.send(json.dumps({
                    "type": "response.create",
                    "response": {
                        "modalities": ["text"],  # Text only for initial setup
                        "instructions": "You MUST call the interview_guidance tool RIGHT NOW before doing anything else. This is mandatory."
                    }
                }))
                
                # Handle events from OpenAI
                await self.handle_openai_events()
                
        except Exception as e:
            print(f"❌ [{self.session.session_id[:8]}] Error connecting to OpenAI: {e}")
            await self.send_to_client({
                "type": "error",
                "message": f"Failed to connect to OpenAI: {str(e)}"
            })
    
    async def handle_openai_events(self):
        """Handle events from OpenAI Realtime API"""
        try:
            async for message in self.openai_ws:
                event = json.loads(message)
                await self.process_openai_event(event)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 [{self.session.session_id[:8]}] OpenAI connection closed")
        except Exception as e:
            print(f"❌ [{self.session.session_id[:8]}] Error handling OpenAI events: {e}")
    
    async def process_openai_event(self, event: dict):
        """Process a single event from OpenAI"""
        event_type = event.get("type")
        
        # Log ALL non-audio events for debugging
        if event_type not in ["response.audio.delta", "response.audio_transcript.delta", "input_audio_buffer.speech_started", "input_audio_buffer.speech_stopped"]:
            if "function" in event_type.lower() or "tool" in event_type.lower() or "output_item" in event_type:
                # Function/tool/output events - show FULL detail  
                print(f"🔔🔔🔔 [{self.session.session_id[:8]}] *** TOOL/FUNCTION EVENT: {event_type} ***")
                print(json.dumps(event, indent=2))
                print("="*80)
            else:
                # Other events - just log type for context
                print(f"📨 [{self.session.session_id[:8]}] Event: {event_type}")
        
        # Handle events (separate from logging)
        if event_type == "response.audio.delta":
            # Forward AI audio to client
            chunk_size = len(event.get("delta", ""))
            print(f"🔊 [{self.session.session_id[:8]}] Audio chunk: {chunk_size} bytes")
            await self.send_to_client({
                "type": "ai_audio",
                "audio": event.get("delta", ""),
                "response_id": event.get("response_id")
            })
        
        elif event_type == "response.audio.done":
            # Audio generation complete
            print(f"✅ [{self.session.session_id[:8]}] Audio generation done")
            pass  # Just log, no action needed
        
        elif event_type == "response.audio_transcript.delta":
            # Accumulate transcript
            delta = event.get("delta", "")
            if delta:
                self.session.transcript_buffer += delta
        
        elif event_type == "response.audio_transcript.done":
            # Send complete AI transcript to client
            if self.session.transcript_buffer:
                ai_text = self.session.transcript_buffer
                print(f"🤖 [{self.session.session_id[:8]}] AI: {ai_text[:50]}...")
                
                await self.send_to_client({
                    "type": "ai_transcript",
                    "text": ai_text
                })
                
                # Store in conversation history (only if not during assessment)
                if self.session.assessment_state.current_state == AssessmentState.INACTIVE:
                    self.session.add_conversation_turn("AI", ai_text)
                
                self.session.transcript_buffer = ""
        
        elif event_type == "conversation.item.input_audio_transcription.delta":
            # User speech transcription delta (incremental)
            # We should accumulate these like we do for AI transcript
            delta = event.get("delta", "")
            if delta:
                # Accumulate in a user transcript buffer
                if not hasattr(self.session, 'user_transcript_buffer'):
                    self.session.user_transcript_buffer = ""
                self.session.user_transcript_buffer += delta
        
        elif event_type == "conversation.item.input_audio_transcription.completed":
            # User speech transcription completed
            # Use the accumulated buffer if available, otherwise use the completed transcript
            if hasattr(self.session, 'user_transcript_buffer') and self.session.user_transcript_buffer:
                transcript = self.session.user_transcript_buffer
                self.session.user_transcript_buffer = ""  # Reset buffer
            else:
                transcript = event.get("transcript", "")
            
            print(f"👤 [{self.session.session_id[:8]}] User: {transcript[:50]}...")
            
            await self.send_to_client({
                "type": "user_transcript",
                "text": transcript
            })
            
            # Store in conversation history (only if not during assessment)
            if self.session.assessment_state.current_state == AssessmentState.INACTIVE:
                self.session.add_conversation_turn("User", transcript)
        
        elif event_type == "response.function_call_arguments.done":
            # Handle function calls
            print(f"📞 [{self.session.session_id[:8]}] Detected function call event")
            await self.handle_function_call(event)
        
        elif event_type == "response.output_item.done":
            # Alternative event for function calls
            item = event.get("item", {})
            if item.get("type") == "function_call":
                print(f"📞 [{self.session.session_id[:8]}] Detected function call via output_item.done")
                await self.handle_function_call(event)
        
        elif event_type == "response.done":
            # Response complete
            self.response_in_progress = False
            await self.send_to_client({
                "type": "response_complete"
            })
        
        elif event_type == "error":
            error = event.get("error", {})
            print(f"❌ [{self.session.session_id[:8]}] OpenAI Error: {error.get('message', 'Unknown')}")
            await self.send_to_client({
                "type": "error",
                "message": error.get("message", "Unknown error")
            })
    
    async def handle_function_call(self, event: dict):
        """Handle function/tool calls from OpenAI"""
        # Debug: print full event structure
        print(f"🔍 [{self.session.session_id[:8]}] Function call event: {json.dumps(event, indent=2)}")
        
        # Extract function call info - try multiple possible structures
        function_call = event.get("function_call", {})
        item = event.get("item", {})
        
        # Function name can be in different places
        function_name = (
            function_call.get("name", "") or
            item.get("name", "") or
            event.get("name", "")
        )
        
        # Call ID can also be in different places
        call_id = (
            function_call.get("call_id") or 
            function_call.get("id") or
            item.get("call_id") or
            item.get("id") or
            event.get("call_id") or
            event.get("item_id")
        )
        
        print(f"🔧 [{self.session.session_id[:8]}] Function call: {function_name} (call_id: {call_id})")
        
        if not function_name:
            print(f"⚠️ [{self.session.session_id[:8]}] No function name found in event!")
            return
        
        if function_name == "interview_guidance":
            guidance_text = get_interview_guidance()
            self.session.guidance_loaded = True
            await self.send_tool_output(call_id, guidance_text)
            print(f"🧭 [{self.session.session_id[:8]}] Interview guidance loaded")
            
            # Notify client that setup is complete
            await self.send_to_client({
                "type": "setup_complete",
                "message": "Interview protocol loaded. Ready for conversation!"
            })
        
        elif function_name == "trigger_assessment":
            print(f"🔔 [{self.session.session_id[:8]}] trigger_assessment called!")
            
            # Extract reason
            arguments = function_call.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except:
                    arguments = {}
            reason = arguments.get("reason", "Linguistic ceiling reached")
            
            print(f"📊 [{self.session.session_id[:8]}] Assessment reason: {reason}")
            
            # Trigger assessment
            if self.session.assessment_state.trigger_assessment(reason):
                print(f"✅ [{self.session.session_id[:8]}] Assessment state machine triggered")
                
                # DON'T send acknowledgment here - go straight to assessment
                # The old flow caused the AI to keep repeating the acknowledgment
                
                # Notify client
                await self.send_to_client({
                    "type": "assessment_triggered",
                    "message": "Generating assessment..."
                })
                print(f"📱 [{self.session.session_id[:8]}] Client notified")
                
                # Send empty tool output to complete this function call
                await self.send_tool_output(
                    call_id,
                    "Assessment triggered. Now generating report..."
                )
                
                # Generate assessment in background (don't block WebSocket)
                print(f"🚀 [{self.session.session_id[:8]}] Launching assessment generation...")
                task = asyncio.create_task(self._generate_and_deliver_assessment())
                self.background_tasks.add(task)
                task.add_done_callback(self.background_tasks.discard)
            else:
                print(f"⚠️ [{self.session.session_id[:8]}] Assessment already triggered, ignoring duplicate")
    
    async def _generate_and_deliver_assessment(self):
        """Generate assessment report and deliver it (runs in background)"""
        keepalive_task = None
        try:
            print(f"🔍 [{self.session.session_id[:8]}] Starting assessment generation...")
            
            # Start keepalive task to prevent WebSocket timeout
            keepalive_task = asyncio.create_task(self._keepalive_during_assessment())
            self.background_tasks.add(keepalive_task)
            keepalive_task.add_done_callback(self.background_tasks.discard)
            
            # Short delay to let WebSocket stabilize
            await asyncio.sleep(1.0)
            
            # Send progress update
            await self.send_to_client({
                "type": "assessment_progress",
                "message": "Analyzing conversation...",
                "progress": 0.3
            })
            
            # Generate report (this can take 5-10 seconds)
            print(f"🧠 [{self.session.session_id[:8]}] Calling assessment agent...")
            conversation_history = self.session.get_conversation_history()
            print(f"📊 [{self.session.session_id[:8]}] Conversation length: {len(conversation_history)} turns")
            
            report = self.assessment_agent.generate_assessment(conversation_history)
            print(f"✅ [{self.session.session_id[:8]}] Report generated")
            
            # Send progress update
            await self.send_to_client({
                "type": "assessment_progress",
                "message": "Generating summary...",
                "progress": 0.7
            })
            
            verbal_summary = self.assessment_agent.report_to_verbal_summary(report)
            print(f"📝 [{self.session.session_id[:8]}] Verbal summary created")
            print(f"📋 [{self.session.session_id[:8]}] Assessment complete: {report.proficiency_level}")
            
            # FIX #3: Stop keepalive and await cancellation properly
            if keepalive_task and not keepalive_task.done():
                print(f"🛑 [{self.session.session_id[:8]}] Stopping keepalive task...")
                keepalive_task.cancel()
                try:
                    await keepalive_task
                except asyncio.CancelledError:
                    print(f"✅ [{self.session.session_id[:8]}] Keepalive cancelled cleanly")
                    pass
            
            # FIX #1: Only cancel if there's actually a response in progress
            if self.response_in_progress:
                try:
                    print(f"🔇 [{self.session.session_id[:8]}] Cancelling active response...")
                    await self.openai_ws.send(json.dumps({
                        "type": "response.cancel"
                    }))
                    self.response_in_progress = False  # Force clear immediately
                    await asyncio.sleep(0.5)  # FIX #2: Longer wait (500ms instead of 300ms)
                    print(f"✅ [{self.session.session_id[:8]}] Response cancelled")
                except Exception as e:
                    print(f"⚠️ [{self.session.session_id[:8]}] Could not cancel response: {e}")
                    self.response_in_progress = False  # Force clear on error
            else:
                print(f"ℹ️ [{self.session.session_id[:8]}] No active response to cancel")
            
            # FIX #4: Clear any lingering audio buffers
            try:
                await self.openai_ws.send(json.dumps({
                    "type": "input_audio_buffer.clear"
                }))
                await asyncio.sleep(0.2)  # Let buffer clear
            except Exception as e:
                print(f"⚠️ [{self.session.session_id[:8]}] Could not clear audio buffer: {e}")
            
            # CRITICAL: Send report to client FIRST (before trying to speak)
            # This ensures the visual report shows even if speech fails
            await self.send_to_client({
                "type": "assessment_complete",
                "report": report.model_dump(),
                "summary": verbal_summary
            })
            print(f"✅ [{self.session.session_id[:8]}] Assessment report sent to client")
            
            # Save report to file
            self.session.save_assessment_report(report, verbal_summary)
            
            # Now try to speak the summary in the background (non-blocking)
            # If this fails, the visual report is already showing
            try:
                print(f"🗣️ [{self.session.session_id[:8]}] Sending summary to be spoken...")
                await self.send_text_message(verbal_summary, language="english")
                print(f"✅ [{self.session.session_id[:8]}] Summary sent for speech")
            except Exception as e:
                print(f"⚠️ [{self.session.session_id[:8]}] Could not send summary for speech: {e}")
                print(f"ℹ️ [{self.session.session_id[:8]}] Visual report is still displayed to user")
            
        except asyncio.CancelledError:
            print(f"🛑 [{self.session.session_id[:8]}] Assessment generation cancelled")
            # FIX #3: Proper keepalive cleanup on cancellation
            if keepalive_task and not keepalive_task.done():
                keepalive_task.cancel()
                try:
                    await keepalive_task
                except asyncio.CancelledError:
                    print(f"✅ [{self.session.session_id[:8]}] Keepalive cancelled in exception handler")
                    pass
            # Don't re-raise during shutdown
            if not self.is_shutting_down:
                raise
            
        except Exception as e:
            print(f"❌ [{self.session.session_id[:8]}] Assessment generation error: {e}")
            import traceback
            traceback.print_exc()
            
            # FIX #3: Stop keepalive with proper awaiting
            if keepalive_task and not keepalive_task.done():
                keepalive_task.cancel()
                try:
                    await keepalive_task
                except asyncio.CancelledError:
                    print(f"✅ [{self.session.session_id[:8]}] Keepalive cancelled in error handler")
                    pass
            
            # Notify client of error
            try:
                await self.send_to_client({
                    "type": "error",
                    "message": "Assessment generation failed. Please try ending the session."
                })
            except:
                pass
            
            # Try to tell user
            try:
                await self.send_text_message(
                    "I apologize, there was an error generating your assessment. Please try ending the session and starting a new one.",
                    language="english"
                )
            except:
                pass
    
    async def _keepalive_during_assessment(self):
        """Send periodic keepalive messages during assessment generation"""
        try:
            while not self.is_shutting_down:
                await asyncio.sleep(3.0)  # Send keepalive every 3 seconds
                
                # Send a harmless message to keep WebSocket alive
                try:
                    # Ping both connections
                    if self.openai_ws:
                        # Send empty audio buffer clear (harmless, keeps connection alive)
                        await self.openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.clear"
                        }))
                    
                    if self.client_ws:
                        # Send keepalive to client
                        await self.send_to_client({
                            "type": "keepalive",
                            "message": "Assessment in progress..."
                        })
                    
                    print(f"💓 [{self.session.session_id[:8]}] Keepalive sent")
                except Exception as e:
                    print(f"⚠️ [{self.session.session_id[:8]}] Keepalive failed: {e}")
                    break
                    
        except asyncio.CancelledError:
            print(f"🛑 [{self.session.session_id[:8]}] Keepalive task cancelled")
            # Don't re-raise during shutdown
            if not self.is_shutting_down:
                raise
    
    async def send_tool_output(self, call_id: str, output_text: str):
        """Send tool output back to OpenAI"""
        if not call_id:
            return
        
        tool_output_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": output_text
            }
        }
        await self.openai_ws.send(json.dumps(tool_output_event))
        
        # Request follow-up response (only if not already in progress)
        if not self.response_in_progress:
            self.response_in_progress = True
            await self.openai_ws.send(json.dumps({
                "type": "response.create",
                "response": {"modalities": ["text", "audio"]}
            }))
        else:
            print(f"⚠️ [{self.session.session_id[:8]}] Skipping response.create - already in progress")
    
    async def send_text_message(self, text: str, language: str = "auto"):
        """Send text message for AI to speak"""
        # FIX #4: Wait longer if response is in progress
        retries = 0
        while self.response_in_progress and retries < 20:  # Increased from 10 to 20
            await asyncio.sleep(0.1)
            retries += 1
        
        if self.response_in_progress:
            print(f"⚠️ [{self.session.session_id[:8]}] Response still in progress after 2s, forcing clear")
            self.response_in_progress = False
        
        # Determine voice and language instruction based on language
        if language == "english":
            voice = "alloy"  # Native English voice
            lang_instruction = "You are a native American English speaker with clear, natural pronunciation. Speak this assessment summary in professional, clear American English: "
        elif language == "korean":
            voice = "marin"  # Keep Korean voice for Korean
            lang_instruction = "Speak this in Korean: "
        else:
            # Auto-detect based on text
            ascii_ratio = sum(1 for c in text if ord(c) < 128) / len(text) if text else 0
            if ascii_ratio > 0.7:
                voice = "alloy"
                lang_instruction = "Speak this in natural American English pronunciation: "
            else:
                voice = "marin"
                lang_instruction = "Speak this naturally: "
        
        # FIX #5: Improved voice switching with proper guards and timing
        if voice != "marin":
            try:
                print(f"🎤 [{self.session.session_id[:8]}] Preparing to switch voice to: {voice}")
                
                # FIX #1: Only cancel if there's actually a response
                if self.response_in_progress:
                    print(f"🔇 [{self.session.session_id[:8]}] Cancelling active response before voice switch...")
                    await self.openai_ws.send(json.dumps({
                        "type": "response.cancel"
                    }))
                    self.response_in_progress = False  # Force clear
                    await asyncio.sleep(0.5)  # FIX #2: Longer wait
                
                # Now switch voice
                await self.openai_ws.send(json.dumps({
                    "type": "session.update",
                    "session": {
                        "voice": voice
                    }
                }))
                print(f"✅ [{self.session.session_id[:8]}] Voice switched to: {voice}")
                await asyncio.sleep(0.5)  # FIX #2: Longer wait for voice change to apply (was 0.3)
                
            except Exception as e:
                # Voice switch failed, but continue anyway with stronger instructions
                print(f"⚠️ [{self.session.session_id[:8]}] Voice switch failed (continuing with instructions): {e}")
        
        # Send transcript to client IMMEDIATELY (before OpenAI responds)
        # This prevents lag between audio and transcript display
        await self.send_to_client({
            "type": "ai_transcript",
            "text": text  # Send the actual text, not the instruction
        })
        print(f"📝 [{self.session.session_id[:8]}] Sent transcript to client (pre-audio)")
        
        self.response_in_progress = True
        response_event = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "instructions": f"{lang_instruction}{text}"
            }
        }
        await self.openai_ws.send(json.dumps(response_event))
    
    async def handle_client_audio(self, audio_data: str):
        """Handle audio from client (PTT message)"""
        try:
            # Send audio to OpenAI
            await self.openai_ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": audio_data
            }))
            
            # Commit the audio (trigger processing)
            await self.openai_ws.send(json.dumps({
                "type": "input_audio_buffer.commit"
            }))
            
            # Request response (only if not already in progress)
            if not self.response_in_progress:
                self.response_in_progress = True
                await self.openai_ws.send(json.dumps({
                    "type": "response.create",
                    "response": {"modalities": ["text", "audio"]}
                }))
            else:
                print(f"⚠️ [{self.session.session_id[:8]}] Skipping response.create - already in progress")
            
        except Exception as e:
            if not self.is_shutting_down:
                print(f"❌ [{self.session.session_id[:8]}] Error handling client audio: {e}")
    
    async def cleanup(self):
        """Cleanup this bridge and cancel all background tasks"""
        print(f"🧹 [{self.session.session_id[:8]}] Cleaning up bridge...")
        self.is_shutting_down = True
        
        # Cancel all tracked background tasks
        for task in list(self.background_tasks):
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to finish (with timeout)
        if self.background_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.background_tasks, return_exceptions=True),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                print(f"⚠️ [{self.session.session_id[:8]}] Some tasks didn't finish in time")
            except Exception as e:
                print(f"⚠️ [{self.session.session_id[:8]}] Error during cleanup: {e}")
        
        print(f"✅ [{self.session.session_id[:8]}] Bridge cleanup complete")
    
    async def send_to_client(self, message: dict):
        """Send message to browser client"""
        try:
            await self.client_ws.send_json(message)
        except Exception as e:
            print(f"⚠️ [{self.session.session_id[:8]}] Error sending to client: {e}")
