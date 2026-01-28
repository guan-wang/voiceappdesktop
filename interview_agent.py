"""
Interview Agent - Handles real-time voice conversation with OpenAI Realtime API
Manages audio I/O, WebSocket connection, and conversation flow
"""

import os
import asyncio
import json
import uuid
from datetime import datetime
from openai import OpenAI
import websockets
import ssl
import certifi
import base64
import pyaudio
import queue
from tools.interview_guidance import get_interview_guidance
from assessment_agent import AssessmentAgent
from assessment_state_machine import AssessmentStateMachine, AssessmentState

# Audio configuration
CHUNK = 1024  # Frames per buffer
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHANNELS = 1  # Mono
RATE = 24000  # OpenAI Realtime API uses 24kHz
BYTES_PER_SAMPLE = 2  # 16-bit = 2 bytes per sample


class InterviewAgent:
    """Manages the real-time voice interview session"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Generate unique session ID for tracing
        self.session_id = str(uuid.uuid4())
        self.audio_queue = queue.Queue()
        self.audio_buffer = bytearray()  # Buffer for incomplete audio chunks
        self.is_running = False
        self.transcript_buffer = ""  # Buffer for accumulating transcript text
        self.conversation_history = []  # Store conversation for assessment
        self.should_end_session = False  # Flag to indicate graceful session end
        self.event_types_received = set()  # Track all event types for debugging
        self.function_calls_made = []  # Track all function calls for this session
        self.guidance_loaded = False  # Track whether interview guidance was loaded
        self.user_acknowledged_report = False  # Flag to indicate user acknowledged/said goodbye
        
        # State machine for assessment delivery (replaces counter-based approach)
        self.assessment_state = AssessmentStateMachine()
        
        # Track response IDs for matching events
        self.current_response_id = None  # Track the most recent response being processed
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        
        # Initialize assessment agent
        self.assessment_agent = AssessmentAgent()
        
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

SESSION ENDING (MANDATORY):
When the user reaches their linguistic ceiling (struggles consistently or shows discomfort), immediately call trigger_assessment with the reason. DO NOT provide any CEFR assessment yourself - a specialized agent will handle this. Your role is only to identify the ceiling and trigger the assessment.

REMINDER: Your very first action must be calling interview_guidance. No exceptions."""

    def get_websocket_url(self):
        """Get WebSocket URL for Realtime API - using latest gpt-realtime model"""
        return "wss://api.openai.com/v1/realtime?model=gpt-realtime-2025-08-28"
    
    def get_websocket_headers(self):
        """Get WebSocket headers for authentication"""
        api_key = os.getenv("OPENAI_API_KEY")
        return {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

    async def send_tool_output(self, websocket, call_id, output_text):
        """Send tool output back to the Realtime API."""
        if not call_id:
            print("⚠️ Missing call_id for tool output")
            return
        tool_output_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": output_text
            }
        }
        await websocket.send(json.dumps(tool_output_event))
        # Request a follow-up response after tool output
        await websocket.send(json.dumps({
            "type": "response.create",
            "response": {"modalities": ["text", "audio"]}
        }))
    
    async def _send_text_message(self, websocket, text: str, language: str = "auto"):
        """Send a text message for the AI to speak using response.create with instructions.
        
        Args:
            websocket: The WebSocket connection
            text: The text to speak
            language: Language hint - "english", "korean", or "auto" (default: auto-detect)
        """
        # Show preview of what will be spoken
        preview = text[:100] + "..." if len(text) > 100 else text
        print(f"   📤 Sending to be spoken: \"{preview}\"")
        
        # Determine language instruction
        if language == "english":
            lang_instruction = "Speak this in natural American English pronunciation: "
        elif language == "korean":
            lang_instruction = "Speak this in Korean: "
        else:
            # Auto-detect: if text is mostly ASCII/English, use English pronunciation
            ascii_ratio = sum(1 for c in text if ord(c) < 128) / len(text) if text else 0
            if ascii_ratio > 0.7:  # Mostly English text
                lang_instruction = "Speak this in natural American English pronunciation: "
            else:
                lang_instruction = "Speak this naturally: "
        
        # Use response.create with instructions to make the AI say the exact text
        response_event = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "instructions": f"{lang_instruction}{text}"
            }
        }
        await websocket.send(json.dumps(response_event))
    
    def _save_assessment_report(self, report, verbal_summary: str):
        """Save assessment report to file for reference."""
        try:
            # Create reports directory if it doesn't exist
            reports_dir = os.path.join(os.path.dirname(__file__), "reports")
            os.makedirs(reports_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(reports_dir, f"assessment_{timestamp}.json")
            
            # Convert report to dict and save
            report_dict = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "report": report.model_dump(),
                "verbal_summary": verbal_summary,
                "conversation_length": len(self.conversation_history)
            }
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Assessment report saved to: {report_path}")
            
        except Exception as e:
            print(f"⚠️ Error saving report: {e}")

    def setup_audio_streams(self):
        """Setup audio input and output streams"""
        try:
            # Input stream (microphone) - no callback, we'll read directly
            self.input_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            # Output stream (speakers) - with callback for playback
            self.output_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK,
                stream_callback=self.audio_output_callback
            )
            
            print("✅ Audio streams initialized")
            
        except Exception as e:
            print(f"❌ Error setting up audio: {e}")
            raise

    def audio_output_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio output - plays audio from API"""
        # Calculate how many bytes we need (frame_count * bytes_per_sample * channels)
        bytes_needed = frame_count * BYTES_PER_SAMPLE * CHANNELS
        
        # First, try to get data from buffer
        if len(self.audio_buffer) >= bytes_needed:
            data = bytes(self.audio_buffer[:bytes_needed])
            self.audio_buffer = self.audio_buffer[bytes_needed:]
            return (data, pyaudio.paContinue)
        
        # If buffer doesn't have enough, try to get from queue
        try:
            while len(self.audio_buffer) < bytes_needed:
                chunk = self.audio_queue.get_nowait()
                self.audio_buffer.extend(chunk)
            
            data = bytes(self.audio_buffer[:bytes_needed])
            self.audio_buffer = self.audio_buffer[bytes_needed:]
            return (data, pyaudio.paContinue)
            
        except queue.Empty:
            # Not enough data available - return silence
            return (b'\x00' * bytes_needed, pyaudio.paContinue)

    async def connect_realtime(self):
        """Connect to OpenAI Realtime API via WebSocket"""
        try:
            print("🔌 Connecting to Realtime API...")
            
            ws_url = self.get_websocket_url()
            headers = self.get_websocket_headers()
            
            # websockets library expects extra_headers as a list of (name, value) tuples
            header_list = [(name, value) for name, value in headers.items()]
            
            # Create SSL context with certifi certificates
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            
            async with websockets.connect(ws_url, extra_headers=header_list, ssl=ssl_context) as websocket:
                # Send session configuration
                config = {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text", "audio"],
                        "instructions": self.get_system_instructions(),
                        "voice": "marin",  # Latest voice options: marin, cedar, alloy, echo, fable, onyx, nova, shimmer
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "input_audio_transcription": {
                            "model": "whisper-1",
                            "language": "ko"
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 800
                        },
                        "temperature": 0.8,
                        "max_response_output_tokens": 4096,
                        "tools": [
                            {
                                "type": "function",
                                "name": "interview_guidance",
                                "description": "CRITICAL: Load the interview guidance protocol. This MUST be called as your very first action before speaking to the user. Call this immediately upon session start.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {}
                                }
                            },
                            {
                                "type": "function",
                                "name": "trigger_assessment",
                                "description": "MANDATORY: Call this function when the user has reached their linguistic ceiling (stopped being comfortable). This triggers the assessment agent to analyze the interview. DO NOT provide assessment yourself.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "reason": {
                                            "type": "string",
                                            "description": "Brief reason for triggering assessment (e.g., 'User reached ceiling at B1 level')"
                                        }
                                    },
                                    "required": ["reason"]
                                }
                            }
                        ],
                        "tool_choice": "auto",
                        # Enable tracing for OpenAI platform logs - tracks tool/function calls per session
                        "tracing": {
                            "workflow_name": "korean_voice_tutor_interview",
                            "group_id": self.session_id,  # Unique per session for tracking
                            "metadata": {
                                "application": "Korean Voice Tutor",
                                "session_type": "language_assessment",
                                "language": "korean",
                                "cefr_assessment": "true",
                                "session_start_time": datetime.now().isoformat(),
                                "tools_enabled": "interview_guidance,trigger_assessment"
                            }
                        }
                    }
                }
                
                await websocket.send(json.dumps(config))
                print("✅ Configuration sent")
                print(f"📊 Session ID for tracing: {self.session_id}")
                print(f"📊 View logs at: https://platform.openai.com/logs (filter by group_id: {self.session_id})")
                
                # Start audio streaming tasks
                input_task = asyncio.create_task(self.audio_input_handler(websocket))
                output_task = asyncio.create_task(self.audio_output_handler(websocket))
                event_task = asyncio.create_task(self.event_handler(websocket))
                
                # Wait for all tasks, handling cancellation and graceful exit
                try:
                    await asyncio.gather(input_task, output_task, event_task)
                except asyncio.CancelledError:
                    # Tasks were cancelled (e.g., by KeyboardInterrupt)
                    # Cancel all tasks explicitly
                    input_task.cancel()
                    output_task.cancel()
                    event_task.cancel()
                    # Wait for cancellation to complete
                    await asyncio.gather(input_task, output_task, event_task, return_exceptions=True)
                    raise
                finally:
                    # If session should end gracefully, stop the running flag
                    if self.should_end_session:
                        self.is_running = False
                        # Cancel tasks to ensure clean exit
                        input_task.cancel()
                        output_task.cancel()
                        event_task.cancel()
                        # Wait for cancellation to complete
                        await asyncio.gather(input_task, output_task, event_task, return_exceptions=True)
                        
        except Exception as e:
            print(f"❌ Error connecting: {e}")
            raise

    async def audio_input_handler(self, websocket):
        """Handle audio input - send to API"""
        try:
            while self.is_running and not self.should_end_session:
                # Skip sending audio during assessment delivery to avoid interference
                if self.assessment_state.current_state not in [
                    AssessmentState.INACTIVE,
                    AssessmentState.COMPLETE
                ]:
                    # During assessment delivery, don't send user audio
                    await asyncio.sleep(0.1)
                    continue
                
                # Read audio from microphone
                data = self.input_stream.read(CHUNK, exception_on_overflow=False)
                
                # Send audio to API
                audio_event = {
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(data).decode('utf-8')
                }
                await websocket.send(json.dumps(audio_event))
                
                await asyncio.sleep(0.01)  # Small delay to prevent overwhelming
                
        except asyncio.CancelledError:
            # Task was cancelled, exit gracefully
            pass
        except Exception as e:
            print(f"❌ Audio input error: {e}")

    async def audio_output_handler(self, websocket):
        """Handle audio output - receive from API"""
        try:
            while self.is_running and not self.should_end_session:
                # This is handled by event_handler receiving audio events
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            # Task was cancelled, exit gracefully
            pass
        except Exception as e:
            print(f"❌ Audio output error: {e}")

    async def event_handler(self, websocket):
        """Handle events from the API"""
        try:
            async for message in websocket:
                event = json.loads(message)
                event_type = event.get("type")
                
                # Track all event types for debugging
                self.event_types_received.add(event_type)
                
                # Debug: Log all function call related events
                if "function" in event_type.lower() or "tool" in event_type.lower():
                    print(f"🔧 [DEBUG] Function/Tool event: {event_type}")
                    print(f"🔧 [DEBUG] Event data: {json.dumps(event, indent=2, ensure_ascii=False)}")
                
                if event_type == "session.created":
                    print("✅ Session created successfully")
                    
                elif event_type == "session.updated":
                    print("✅ Session updated")
                
                elif event_type == "response.created":
                    # Capture response ID for tracking
                    response_id = event.get("response", {}).get("id")
                    if response_id:
                        self.current_response_id = response_id
                        
                        # Register with state machine based on current state
                        current_state = self.assessment_state.current_state
                        if current_state == AssessmentState.TRIGGERED:
                            self.assessment_state.start_acknowledgment_response(response_id)
                        elif current_state == AssessmentState.REPORT_GENERATING:
                            # Summary response being created
                            verbal_summary = self.assessment_state.verbal_summary
                            if verbal_summary:
                                self.assessment_state.start_summary_response(response_id, verbal_summary)
                        elif current_state in [AssessmentState.SUMMARY_SPEAKING, AssessmentState.SUMMARY_SENDING]:
                            # Check if summary audio completed - if so, this is goodbye response
                            tracker = self.assessment_state.response_trackers.get(self.assessment_state.active_response_id)
                            if tracker and tracker.audio_complete:
                                # This is goodbye response
                                self.assessment_state.start_goodbye_response(response_id)
                    
                elif event_type == "response.audio_transcript.delta":
                    # Text transcription of what the AI is saying - accumulate in buffer
                    delta = event.get("delta", "")
                    if delta:
                        self.transcript_buffer += delta
                        
                elif event_type == "response.audio_transcript.done":
                    # Get response ID from event
                    response_id = event.get("response_id", self.current_response_id)
                    
                    # Print the complete sentence when done
                    if self.transcript_buffer:
                        ai_text = self.transcript_buffer
                        print(f"🤖 AI: {ai_text}")
                        # Store in conversation history (only if not during assessment)
                        if self.assessment_state.current_state == AssessmentState.INACTIVE:
                            self.conversation_history.append(("AI", ai_text))
                        
                        self.transcript_buffer = ""  # Reset buffer
                    else:
                        print()  # New line if buffer was empty
                    
                    # CRITICAL: Mark audio complete for this response using state machine
                    # This fires when audio transcript is complete (audio is done!)
                    if response_id and self.assessment_state.current_state != AssessmentState.INACTIVE:
                        self.assessment_state.mark_audio_complete(response_id)
                    
                elif event_type == "response.audio.delta":
                    # Audio data from AI
                    response_id = event.get("response_id", self.current_response_id)
                    audio_data = event.get("delta", "")
                    
                    if audio_data:
                        # Mark audio started (first delta received)
                        if response_id and self.assessment_state.current_state != AssessmentState.INACTIVE:
                            self.assessment_state.mark_audio_started(response_id)
                        
                        try:
                            # Decode base64 audio
                            audio_bytes = base64.b64decode(audio_data)
                            
                            # Track audio bytes for accurate duration calculation
                            if response_id and self.assessment_state.current_state != AssessmentState.INACTIVE:
                                self.assessment_state.track_audio_bytes(response_id, len(audio_bytes))
                            
                            # Verify audio format (should be PCM16, 24kHz, mono)
                            # Each sample is 2 bytes (16-bit), so audio_bytes length should be even
                            if len(audio_bytes) % 2 != 0:
                                print(f"⚠️ Warning: Received odd-length audio chunk: {len(audio_bytes)} bytes")
                                # Pad with zero if odd length
                                audio_bytes += b'\x00'
                            
                            # Add to queue for playback
                            self.audio_queue.put(audio_bytes)
                        except Exception as e:
                            print(f"⚠️ Error processing audio delta: {e}")
                        
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # User's speech transcribed
                    transcript = event.get("transcript", "")
                    print(f"👤 You: {transcript}")
                    
                    # Store in conversation history (only if not during assessment)
                    if self.assessment_state.current_state == AssessmentState.INACTIVE:
                        self.conversation_history.append(("User", transcript))
                    else:
                        # During assessment delivery, check for acknowledgment/goodbye
                        if self._is_user_acknowledgment(transcript):
                            print("✅ User acknowledged the report or said goodbye")
                            self.user_acknowledged_report = True
                            # If user acknowledges, we can end sooner
                            print("\n👋 User acknowledged. Ending session gracefully...")
                            self.should_end_session = True
                            self.is_running = False
                            await asyncio.sleep(1)
                            break
                    
                elif event_type == "error":
                    error = event.get("error", {})
                    print(f"❌ API Error: {error.get('message', 'Unknown error')}")
                    
                elif event_type == "response.done":
                    # Get response ID from event, or use the tracked current response ID
                    response_id = event.get("response_id") or self.current_response_id or "unknown"
                    print(f"✅ Response complete (ID: {response_id[-8:] if response_id != 'unknown' else response_id})")
                    
                    # Mark response complete in state machine
                    if response_id and response_id != "unknown":
                        self.assessment_state.mark_response_complete(response_id)
                    
                    # Handle based on current state
                    current_state = self.assessment_state.current_state
                    
                    if current_state in [AssessmentState.ACK_GENERATING, AssessmentState.ACK_SPEAKING]:
                        # Acknowledgment response completed - wait for audio then generate report
                        print("⏳ Waiting for acknowledgment audio to complete...")
                        audio_ok = await self.assessment_state.wait_for_audio_complete(response_id, timeout=10.0)
                        
                        if audio_ok or current_state == AssessmentState.ACK_SPEAKING:
                            # Start generating report in background to avoid blocking websocket
                            if self.assessment_state.start_report_generation():
                                print("\n🔍 Generating assessment report in background...")
                                
                                # Create background task for assessment generation
                                async def generate_and_send_assessment():
                                    try:
                                        # Generate assessment report (this takes time)
                                        report = self.assessment_agent.generate_assessment(self.conversation_history)
                                        verbal_summary = self.assessment_agent.report_to_verbal_summary(report)
                                        print(f"\n📋 Assessment Summary:\n{verbal_summary}")
                                        
                                        # Save report to file
                                        self._save_assessment_report(report, verbal_summary)
                                        
                                        # Store summary in state machine
                                        self.assessment_state.verbal_summary = verbal_summary
                                        
                                        # Send summary to be spoken (in English)
                                        print("\n🗣️ Sending assessment summary to be spoken...")
                                        await self._send_text_message(websocket, verbal_summary, language="english")
                                        # Response ID will be captured in response.created event
                                    except Exception as e:
                                        print(f"❌ Error in assessment generation: {e}")
                                
                                # Launch as background task so event loop continues
                                asyncio.create_task(generate_and_send_assessment())
                        else:
                            print("⚠️ Acknowledgment audio timeout, but proceeding with report generation")
                    
                    elif current_state in [AssessmentState.SUMMARY_SENDING, AssessmentState.SUMMARY_SPEAKING]:
                        # Summary response completed - wait for audio then send goodbye
                        print("⏳ Waiting for summary audio to complete...")
                        audio_ok = await self.assessment_state.wait_for_audio_complete(response_id, timeout=20.0)
                        
                        if audio_ok or current_state == AssessmentState.SUMMARY_SPEAKING:
                            # Use actual audio duration from received bytes
                            tracker = self.assessment_state.response_trackers.get(response_id)
                            if tracker:
                                actual_duration = tracker.calculate_audio_duration()
                                # Add small buffer (3 seconds) for queue drain and final playback
                                buffer_delay = actual_duration + 3.0
                                print(f"⏳ Ensuring audio playback buffer is fully drained (actual {actual_duration:.1f}s + 3.0s buffer = {buffer_delay:.1f}s)...")
                            else:
                                # Fallback to word-based estimation if tracker not found
                                verbal_summary = self.assessment_state.verbal_summary or ""
                                word_count = len(verbal_summary.split())
                                estimated_duration = (word_count / 2.5) + 3.0
                                buffer_delay = max(5.0, min(estimated_duration, 30.0))
                                print(f"⏳ Ensuring audio playback buffer is fully drained (estimated {buffer_delay:.1f}s for {word_count} words)...")
                            
                            await asyncio.sleep(buffer_delay)
                            
                            # Check if we can send goodbye
                            if self.assessment_state.can_send_goodbye():
                                print("\n👋 Sending goodbye message...")
                                goodbye_msg = "Thank you for completing the interview! Keep practicing, and you'll continue to improve. Goodbye!"
                                await self._send_text_message(websocket, goodbye_msg, language="english")
                                # Response ID will be captured and registered in next response.created event
                        else:
                            print("⚠️ Summary audio timeout, but proceeding with goodbye")
                    
                    elif current_state in [AssessmentState.GOODBYE_SENDING, AssessmentState.GOODBYE_SPEAKING]:
                        # Goodbye response completed - wait for audio then end session
                        print("⏳ Waiting for goodbye audio to complete...")
                        audio_ok = await self.assessment_state.wait_for_audio_complete(response_id, timeout=10.0)
                        
                        # Wait additional time for audio buffer to drain and play completely
                        print("⏳ Ensuring goodbye audio playback buffer is fully drained...")
                        await asyncio.sleep(3.0)  # Give goodbye audio buffer time to play out
                        
                        # Mark assessment complete
                        self.assessment_state.mark_complete()
                        
                        # End session
                        print("\n✅ Assessment delivery complete. Ending session...")
                        self.should_end_session = True
                        self.is_running = False
                        await asyncio.sleep(1)
                        break
                    
                    # Check if user acknowledged early
                    if self.user_acknowledged_report and not self.assessment_state.is_complete():
                        print("\n✅ User acknowledged during assessment. Ending session...")
                        self.assessment_state.mark_complete()
                        self.should_end_session = True
                        self.is_running = False
                        await asyncio.sleep(1)
                        break
                
                elif event_type == "conversation.item.output_audio_transcript.done":
                    # This event fires when the AI's audio transcript is complete
                    # We can check if a function was called here if needed
                    pass
                
                elif event_type == "conversation.item.creation_failed":
                    # Handle creation failures
                    error = event.get("error", {})
                    print(f"⚠️ Item creation failed: {error.get('message', 'Unknown error')}")
                
                elif event_type == "response.function_call_arguments.done":
                    # Function call arguments received - check if it's end_interview
                    print(f"🔧 [DEBUG] Function call arguments done event received")
                    print(f"🔧 [DEBUG] Full event: {json.dumps(event, indent=2, ensure_ascii=False)}")
                    
                    # The event structure: event has "function_call" with "name" and "arguments"
                    function_call = event.get("function_call", {})
                    
                    # Also check alternative event structures
                    if not function_call:
                        function_call = event.get("function_call_arguments", {})
                    if not function_call:
                        # Sometimes the data is at the top level
                        function_call = event
                    
                    function_name = function_call.get("name", "")
                    print(f"🔧 [DEBUG] Function name extracted: '{function_name}'")
                    call_id = (
                        function_call.get("call_id")
                        or function_call.get("id")
                        or event.get("call_id")
                        or event.get("id")
                    )
                    
                    # Track function call for tracing
                    function_call_info = {
                        "function_name": function_name,
                        "timestamp": datetime.now().isoformat(),
                        "event_type": event_type,
                        "arguments": function_call.get("arguments", {})
                    }
                    self.function_calls_made.append(function_call_info)
                    print(f"📊 [TRACE] Function call tracked: {function_name} at {function_call_info['timestamp']}")
                    
                    if function_name == "interview_guidance":
                        guidance_text = get_interview_guidance()
                        self.guidance_loaded = True
                        await self.send_tool_output(websocket, call_id, guidance_text)
                        print("🧭 Interview guidance sent to model")
                    elif function_name == "trigger_assessment":
                        # Extract reason from arguments
                        arguments = function_call.get("arguments", {})
                        if isinstance(arguments, str):
                            try:
                                arguments = json.loads(arguments)
                            except (json.JSONDecodeError, ValueError):
                                arguments = {}
                        reason = arguments.get("reason", "Linguistic ceiling reached") if isinstance(arguments, dict) else "Linguistic ceiling reached"
                        
                        # Trigger assessment state machine
                        if self.assessment_state.trigger_assessment(reason):
                            # Clear any buffered user audio to prevent interference
                            print("🔇 Clearing user audio buffer to prevent interference...")
                            await websocket.send(json.dumps({"type": "input_audio_buffer.clear"}))
                            
                            # Send tool output with instruction for AI to immediately acknowledge
                            print("\n💬 Sending tool output with acknowledgment instruction...")
                            await self.send_tool_output(
                                websocket, 
                                call_id, 
                                "Assessment triggered successfully. Please IMMEDIATELY tell the user in Korean: '평가를 준비하고 있습니다. 잠시만 기다려 주세요.' (Your assessment is being prepared. Please wait a moment.)"
                            )
                            
                            print("💡 Assessment will generate AFTER acknowledgment audio completes.")
                        else:
                            print("⚠️ Assessment already triggered, ignoring duplicate call")
                    else:
                        print(f"🔧 [DEBUG] Function '{function_name}' called (not trigger_assessment)")
                
                elif event_type == "response.function_call.done":
                    # Function call completed - backup check
                    print(f"🔧 [DEBUG] Function call done event received")
                    print(f"🔧 [DEBUG] Full event: {json.dumps(event, indent=2, ensure_ascii=False)}")
                    
                    function_call = event.get("function_call", {})
                    if not function_call:
                        function_call = event.get("function_call_result", {})
                    if not function_call:
                        function_call = event
                    
                    function_name = function_call.get("name", "")
                    print(f"🔧 [DEBUG] Function name extracted: '{function_name}'")
                    
                    # Track function call completion for tracing
                    if function_name:
                        function_call_info = {
                            "function_name": function_name,
                            "timestamp": datetime.now().isoformat(),
                            "event_type": event_type,
                            "status": "completed"
                        }
                        self.function_calls_made.append(function_call_info)
                        print(f"📊 [TRACE] Function call completed: {function_name} at {function_call_info['timestamp']}")
                    
                    # Note: trigger_assessment is fully handled in response.function_call_arguments.done
                    # This is just a backup check in case that event was missed
                    if function_name == "trigger_assessment" and self.assessment_state.current_state == AssessmentState.INACTIVE:
                        print("\n⚠️ Backup: trigger_assessment detected in function_call.done event")
                        # The main handling should have already occurred
                
                # Also check for other function call related events
                elif event_type.startswith("response.function_call"):
                    print(f"🔧 [DEBUG] Other function call event: {event_type}")
                    print(f"🔧 [DEBUG] Event data: {json.dumps(event, indent=2, ensure_ascii=False)}")
                
                # Debug: Log unknown event types (can be removed later)
                elif event_type not in [
                    "session.created", "session.updated",
                    "response.audio_transcript.delta", "response.audio_transcript.done",
                    "response.audio.delta",
                    "conversation.item.input_audio_transcription.completed",
                    "conversation.item.output_audio_transcript.done",
                    "conversation.item.creation_failed",
                    "response.function_call_arguments.done", "response.function_call.done",
                    "error", "response.done"
                ]:
                    # Uncomment for debugging: print(f"🔍 Unknown event type: {event_type}")
                    pass
                    
        except asyncio.CancelledError:
            # Task was cancelled, exit gracefully
            pass
        except Exception as e:
            print(f"❌ Event handler error: {e}")
        finally:
            # Debug: Print all event types received
            print(f"\n🔧 [DEBUG] All event types received: {sorted(self.event_types_received)}")
            if "response.function_call" in str(self.event_types_received):
                print("🔧 [DEBUG] Function call events were received!")
            else:
                print("🔧 [DEBUG] WARNING: No function call events detected!")
            
            # Print function call summary for tracing
            print(f"\n📊 [TRACE SUMMARY] Session ID: {self.session_id}")
            print(f"📊 [TRACE SUMMARY] Total function calls: {len(self.function_calls_made)}")
            if self.function_calls_made:
                print("📊 [TRACE SUMMARY] Function calls made:")
                for i, fc in enumerate(self.function_calls_made, 1):
                    print(f"   {i}. {fc['function_name']} - {fc.get('event_type', 'unknown')} at {fc['timestamp']}")
            else:
                print("📊 [TRACE SUMMARY] ⚠️ No function calls were made in this session")
            print(f"📊 [TRACE SUMMARY] View this session in OpenAI logs: https://platform.openai.com/logs")
            print(f"📊 [TRACE SUMMARY] Filter by group_id: {self.session_id}")

    async def run(self):
        """Main run loop"""
        try:
            print("🇰🇷 Korean Voice Tutor Starting...")
            print("=" * 50)
            
            # Setup audio first
            self.setup_audio_streams()
            
            # Start audio streams
            self.input_stream.start_stream()
            self.output_stream.start_stream()
            
            self.is_running = True
            
            print("\n✅ Ready! Start speaking in Korean...")
            print("Press Ctrl+C to stop, or wait for the interview to complete\n")
            
            # Connect to Realtime API (this will run until interrupted or conversation ends)
            await self.connect_realtime()
            
            # Check if session ended gracefully
            if self.should_end_session:
                print("\n✅ Interview completed naturally. Ending session...")
                
        except KeyboardInterrupt:
            print("\n\n👋 Stopping Korean Voice Tutor...")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Always cleanup
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        self.is_running = False
        self.should_end_session = False  # Reset flag
        
        # Clear any remaining transcript buffer
        self.transcript_buffer = ""
        
        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
            except Exception:
                pass
            
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except Exception:
                pass
            
        if self.audio:
            try:
                self.audio.terminate()
            except Exception:
                pass
            
        print("✅ Cleanup complete")
    
    def _is_user_acknowledgment(self, transcript: str) -> bool:
        """
        Check if user's speech indicates acknowledgment or goodbye during assessment delivery.
        
        Args:
            transcript: The user's transcribed speech
            
        Returns:
            bool: True if user acknowledged or said goodbye
        """
        # Normalize transcript
        transcript_lower = transcript.lower().strip()
        
        # Korean acknowledgment keywords
        korean_keywords = [
            "감사합니다",  # Thank you
            "감사",        # Thanks
            "고마워",      # Thanks (informal)
            "고맙습니다",  # Thank you (formal)
            "알겠습니다",  # I understand
            "알겠어요",    # I understand (polite)
            "알았어요",    # Got it
            "네, 알겠습니다", # Yes, I understand
            "안녕히",      # Goodbye (part of goodbye phrases)
            "안녕",        # Bye
            "잘 가",       # Bye (informal)
            "수고하세요",  # Thank you for your work
            "좋아요",      # Good/Okay
            "괜찮아요",    # It's okay/good
        ]
        
        # English acknowledgment keywords (in case user switches to English)
        english_keywords = [
            "thank",
            "thanks",
            "bye",
            "goodbye",
            "got it",
            "understand",
            "okay",
            "ok",
            "great",
            "good",
            "see you",
        ]
        
        # Check Korean keywords
        for keyword in korean_keywords:
            if keyword in transcript_lower:
                return True
        
        # Check English keywords
        for keyword in english_keywords:
            if keyword in transcript_lower:
                return True
        
        return False
    
    def get_conversation_history(self):
        """Get the conversation history for assessment"""
        return self.conversation_history.copy()