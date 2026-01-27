"""
Realtime Bridge - Connects to OpenAI Realtime API on behalf of web clients
Handles the WebSocket connection and event processing
"""

import os
import json
import base64
import asyncio
import websockets
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
                "voice": "marin",
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
            
            # Use extra_headers parameter (works with websockets 13.x)
            async with websockets.connect(ws_url, extra_headers=extra_headers) as websocket:
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
        
        # Forward relevant events to client
        if event_type == "response.audio.delta":
            # Forward AI audio to client
            await self.send_to_client({
                "type": "ai_audio",
                "audio": event.get("delta", ""),
                "response_id": event.get("response_id")
            })
        
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
        
        elif event_type == "conversation.item.input_audio_transcription.completed":
            # User speech transcribed
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
                
                # Clear audio buffer
                try:
                    await self.openai_ws.send(json.dumps({"type": "input_audio_buffer.clear"}))
                    print(f"🔇 [{self.session.session_id[:8]}] Audio buffer cleared")
                except Exception as e:
                    print(f"⚠️ [{self.session.session_id[:8]}] Failed to clear buffer: {e}")
                
                # Send acknowledgment instruction
                print(f"💬 [{self.session.session_id[:8]}] Sending acknowledgment instruction...")
                try:
                    await self.send_tool_output(
                        call_id,
                        "Assessment triggered successfully. IMMEDIATELY tell the user in Korean: '평가를 준비하고 있습니다. 잠시만 기다려 주세요.' (Your assessment is being prepared. Please wait a moment.)"
                    )
                    print(f"✅ [{self.session.session_id[:8]}] Tool output sent")
                except Exception as e:
                    print(f"❌ [{self.session.session_id[:8]}] Failed to send tool output: {e}")
                
                # Notify client
                await self.send_to_client({
                    "type": "assessment_triggered",
                    "message": "Assessment is being prepared"
                })
                print(f"📱 [{self.session.session_id[:8]}] Client notified")
                
                # Generate assessment in background (don't block WebSocket)
                print(f"🚀 [{self.session.session_id[:8]}] Launching assessment generation...")
                asyncio.create_task(self._generate_and_deliver_assessment())
            else:
                print(f"⚠️ [{self.session.session_id[:8]}] Assessment already triggered, ignoring duplicate")
    
    async def _generate_and_deliver_assessment(self):
        """Generate assessment report and deliver it (runs in background)"""
        keepalive_task = None
        try:
            print(f"🔍 [{self.session.session_id[:8]}] Starting assessment generation...")
            
            # Wait for AI to speak acknowledgment first
            await asyncio.sleep(2.0)
            
            # Start keepalive task to prevent WebSocket timeout
            keepalive_task = asyncio.create_task(self._keepalive_during_assessment())
            
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
            
            # Stop keepalive
            if keepalive_task:
                keepalive_task.cancel()
            
            # Send summary to be spoken
            print(f"🗣️ [{self.session.session_id[:8]}] Sending summary to be spoken...")
            await self.send_text_message(verbal_summary, language="english")
            
            # Send report to client
            await self.send_to_client({
                "type": "assessment_complete",
                "report": report.model_dump(),
                "summary": verbal_summary
            })
            print(f"✅ [{self.session.session_id[:8]}] Assessment delivered")
            
            # Save report to file
            self.session.save_assessment_report(report, verbal_summary)
            
        except Exception as e:
            print(f"❌ [{self.session.session_id[:8]}] Assessment generation error: {e}")
            import traceback
            traceback.print_exc()
            
            # Stop keepalive if running
            if keepalive_task:
                keepalive_task.cancel()
            
            # Notify client of error
            await self.send_to_client({
                "type": "error",
                "message": "Assessment generation failed. Please try ending the session."
            })
            
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
            while True:
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
        
        # Request follow-up response
        await self.openai_ws.send(json.dumps({
            "type": "response.create",
            "response": {"modalities": ["text", "audio"]}
        }))
    
    async def send_text_message(self, text: str, language: str = "auto"):
        """Send text message for AI to speak"""
        # Determine language instruction
        if language == "english":
            lang_instruction = "Speak this in natural American English pronunciation: "
        elif language == "korean":
            lang_instruction = "Speak this in Korean: "
        else:
            ascii_ratio = sum(1 for c in text if ord(c) < 128) / len(text) if text else 0
            lang_instruction = "Speak this in natural American English pronunciation: " if ascii_ratio > 0.7 else "Speak this naturally: "
        
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
            
            # Request response
            await self.openai_ws.send(json.dumps({
                "type": "response.create",
                "response": {"modalities": ["text", "audio"]}
            }))
            
        except Exception as e:
            print(f"❌ [{self.session.session_id[:8]}] Error handling client audio: {e}")
    
    async def send_to_client(self, message: dict):
        """Send message to browser client"""
        try:
            await self.client_ws.send_json(message)
        except Exception as e:
            print(f"⚠️ [{self.session.session_id[:8]}] Error sending to client: {e}")
