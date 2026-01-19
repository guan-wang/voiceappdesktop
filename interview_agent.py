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
import base64
import pyaudio
import queue
from tools.interview_guidance import get_interview_guidance

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
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        
    def get_system_instructions(self):
        """System instructions for the Korean language tutor"""
        return """You are a friendly, casual AI Korean language interviewer. Your goal is to conduct a less than 5-minute voice-based interview in Korean to determine the user's CEFR level.

Before your first response to the user, you MUST call the interview_guidance tool from korean_voice_tutor/tools/interview_guidance.py to load the interview guideline text. Do not speak until you have called the tool and received its output. 
Use the returned guidance as the source of interview rules for the rest of the session.

CRITICAL ENDING INSTRUCTION:
After you provide the CEFR level assessment and say goodbye, you MUST call the end_interview function to properly terminate the session. The function call is mandatory - the session will not end automatically without it.
"""

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
            
            # websockets library expects additional_headers as a list of (name, value) tuples
            header_list = [(name, value) for name, value in headers.items()]
            
            async with websockets.connect(ws_url, additional_headers=header_list) as websocket:
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
                                "description": "Load interview guidance from korean_voice_tutor/tools/interview_guidance.py. This must be called before the AI's first response.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {}
                                }
                            },
                            {
                                "type": "function",
                                "name": "end_interview",
                                "description": "MANDATORY: You MUST call this function when you have completed the interview assessment and said goodbye. This is the ONLY way to properly end the session. Call this immediately after providing the CEFR level assessment and saying farewell.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "reason": {
                                            "type": "string",
                                            "description": "Reason for ending (e.g., 'Interview completed', 'Assessment provided')"
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
                                "tools_enabled": "interview_guidance,end_interview"
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
                    
                elif event_type == "response.audio_transcript.delta":
                    # Text transcription of what the AI is saying - accumulate in buffer
                    delta = event.get("delta", "")
                    if delta:
                        self.transcript_buffer += delta
                        
                elif event_type == "response.audio_transcript.done":
                    # Print the complete sentence when done
                    if self.transcript_buffer:
                        ai_text = self.transcript_buffer
                        print(f"🤖 AI: {ai_text}")
                        # Store in conversation history
                        self.conversation_history.append(("AI", ai_text))
                        
                        # Check for interview completion marker (fallback method)
                        # This is a backup in case function calling doesn't work
                        if "[INTERVIEW_COMPLETE]" in ai_text or "[SESSION_END]" in ai_text:
                            print("\n👋 Interview completion marker detected. Ending session...")
                            self.should_end_session = True
                            self.is_running = False
                            # Wait a moment for any final audio to complete
                            await asyncio.sleep(2)
                            break  # Exit the event handler loop
                        
                        self.transcript_buffer = ""  # Reset buffer
                    else:
                        print()  # New line if buffer was empty
                    
                elif event_type == "response.audio.delta":
                    # Audio data from AI
                    audio_data = event.get("delta", "")
                    if audio_data:
                        try:
                            # Decode base64 audio
                            audio_bytes = base64.b64decode(audio_data)
                            
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
                    # Store in conversation history
                    self.conversation_history.append(("User", transcript))
                    
                elif event_type == "error":
                    error = event.get("error", {})
                    print(f"❌ API Error: {error.get('message', 'Unknown error')}")
                    
                elif event_type == "response.done":
                    print("✅ Response complete")
                
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
                    elif function_name == "end_interview":
                        # Try to get reason from arguments
                        arguments = function_call.get("arguments", {})
                        if isinstance(arguments, str):
                            try:
                                arguments = json.loads(arguments)
                            except (json.JSONDecodeError, ValueError):
                                arguments = {}
                        reason = arguments.get("reason", "Interview completed") if isinstance(arguments, dict) else "Interview completed"
                        print(f"\n👋 Interview ending (function called): {reason}")
                        print("Session will close shortly...")
                        self.should_end_session = True
                        self.is_running = False  # Stop the running flag immediately
                        # Wait a moment for any final audio to complete
                        await asyncio.sleep(2)
                        break  # Exit the event handler loop
                    else:
                        print(f"🔧 [DEBUG] Function '{function_name}' called (not end_interview)")
                
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
                    
                    if function_name == "end_interview" and not self.should_end_session:
                        print("\n👋 Interview ending (function call completed)...")
                        self.should_end_session = True
                        self.is_running = False
                        await asyncio.sleep(2)
                        break
                
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
    
    def get_conversation_history(self):
        """Get the conversation history for assessment"""
        return self.conversation_history.copy()