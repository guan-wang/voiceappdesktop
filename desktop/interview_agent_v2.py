"""
Refactored Interview Agent - Orchestrates real-time voice conversation
This version uses modular components for better maintainability
"""

import os
import asyncio
import json
import base64
import websockets
import ssl
import certifi
from datetime import datetime

import sys
import os
# Add parent directory to path to import from core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio import AudioManager
from session import SessionManager
from websocket import EventDispatcher
from core import AssessmentAgent, AssessmentStateMachine, AssessmentState
from core.prompt_loader import load_interview_system_prompt


class InterviewAgent:
    """Orchestrates the real-time voice interview session"""
    
    def __init__(self):
        """Initialize the interview agent with modular components"""
        # Core components
        self.audio_manager = AudioManager()
        self.session = SessionManager()
        self.assessment_agent = AssessmentAgent()
        self.assessment_state = AssessmentStateMachine()
        
        # Event dispatcher (will be initialized with websocket context)
        self.event_dispatcher = None
        
    def get_system_instructions(self):
        """System instructions for the Korean language tutor (pre-loaded from core/resources/interview_system_prompt.txt)"""
        return load_interview_system_prompt()

    def get_websocket_url(self):
        """Get WebSocket URL for Realtime API"""
        return "wss://api.openai.com/v1/realtime?model=gpt-realtime-2025-08-28"
    
    def get_websocket_headers(self):
        """Get WebSocket headers for authentication"""
        api_key = os.getenv("OPENAI_API_KEY")
        return {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

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
                "tracing": {
                    "workflow_name": "korean_voice_tutor_interview",
                    "group_id": self.session.session_id,
                    "metadata": {
                        "application": "Korean Voice Tutor",
                        "session_type": "language_assessment",
                        "language": "korean",
                        "cefr_assessment": "true",
                        "session_start_time": datetime.now().isoformat(),
                        "tools_enabled": "trigger_assessment"
                    }
                }
            }
        }

    async def connect_realtime(self):
        """Connect to OpenAI Realtime API via WebSocket"""
        try:
            print("🔌 Connecting to Realtime API...")
            
            ws_url = self.get_websocket_url()
            headers = self.get_websocket_headers()
            header_list = [(name, value) for name, value in headers.items()]
            
            # Create SSL context with certifi certificates
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            
            async with websockets.connect(ws_url, extra_headers=header_list, ssl=ssl_context) as websocket:
                # Initialize event dispatcher with context
                context = {
                    "audio_manager": self.audio_manager,
                    "session": self.session,
                    "assessment_agent": self.assessment_agent,
                    "assessment_state": self.assessment_state,
                    "websocket": websocket
                }
                self.event_dispatcher = EventDispatcher(context)
                
                # Send session configuration
                config = self.get_session_config()
                await websocket.send(json.dumps(config))
                print("✅ Configuration sent")
                print(f"📊 Session ID for tracing: {self.session.session_id}")
                print(f"📊 View logs at: https://platform.openai.com/logs (filter by group_id: {self.session.session_id})")
                
                # Start audio streaming tasks
                input_task = asyncio.create_task(self.audio_input_handler(websocket))
                output_task = asyncio.create_task(self.audio_output_handler(websocket))
                event_task = asyncio.create_task(self.event_handler(websocket))
                
                # Wait for all tasks
                try:
                    await asyncio.gather(input_task, output_task, event_task)
                except asyncio.CancelledError:
                    input_task.cancel()
                    output_task.cancel()
                    event_task.cancel()
                    await asyncio.gather(input_task, output_task, event_task, return_exceptions=True)
                    raise
                finally:
                    if self.session.should_end_session:
                        self.session.is_running = False
                        input_task.cancel()
                        output_task.cancel()
                        event_task.cancel()
                        await asyncio.gather(input_task, output_task, event_task, return_exceptions=True)
                        
        except Exception as e:
            print(f"❌ Error connecting: {e}")
            raise

    async def audio_input_handler(self, websocket):
        """Handle audio input - send microphone audio to API"""
        try:
            while self.session.is_running and not self.session.should_end_session:
                # Skip sending audio during assessment delivery to avoid interference
                if self.assessment_state.current_state not in [
                    AssessmentState.INACTIVE,
                    AssessmentState.COMPLETE
                ]:
                    await asyncio.sleep(0.1)
                    continue
                
                # Read audio from microphone
                data = self.audio_manager.read_input_chunk()
                if data:
                    # Send audio to API
                    audio_event = {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(data).decode('utf-8')
                    }
                    await websocket.send(json.dumps(audio_event))
                
                await asyncio.sleep(0.01)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ Audio input error: {e}")

    async def audio_output_handler(self, websocket):
        """Handle audio output - placeholder (actual output handled by event dispatcher)"""
        try:
            while self.session.is_running and not self.session.should_end_session:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ Audio output error: {e}")

    async def event_handler(self, websocket):
        """Handle events from the API using event dispatcher"""
        try:
            async for message in websocket:
                event = json.loads(message)
                
                # Dispatch event to appropriate handler
                await self.event_dispatcher.dispatch(event)
                
                # Check for session end conditions
                if self.session.should_end_session:
                    await asyncio.sleep(1)
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ Event handler error: {e}")
        finally:
            # Print trace summary
            self.session.print_trace_summary()

    async def run(self):
        """Main run loop"""
        try:
            print("🇰🇷 Korean Voice Tutor Starting...")
            print("=" * 50)
            
            # Setup audio
            self.audio_manager.setup_streams()
            self.audio_manager.start_streams()
            
            self.session.is_running = True
            
            print("\n✅ Ready! Start speaking in Korean...")
            print("Press Ctrl+C to stop, or wait for the interview to complete\n")
            
            # Connect to Realtime API
            await self.connect_realtime()
            
            if self.session.should_end_session:
                print("\n✅ Interview completed naturally. Ending session...")
                
        except KeyboardInterrupt:
            print("\n\n👋 Stopping Korean Voice Tutor...")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        self.audio_manager.cleanup()
        self.session.reset()
        print("✅ Cleanup complete")


async def main():
    """Entry point"""
    agent = InterviewAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
