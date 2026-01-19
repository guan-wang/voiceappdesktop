"""
Interview Agent (Synchronous Turn-Taking)
Push-to-talk input sent only after recording ends, with streaming AI output.
No barge-in: user cannot record while AI is speaking.
"""

import os
import asyncio
import json
import uuid
import msvcrt
from datetime import datetime
import base64
import pyaudio
import queue
import websockets
from enum import Enum, auto


# Audio configuration
CHUNK = 1024  # Frames per buffer
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHANNELS = 1  # Mono
RATE = 24000  # OpenAI Realtime API uses 24kHz
BYTES_PER_SAMPLE = 2  # 16-bit = 2 bytes per sample


class State(Enum):
    IDLE = auto()
    RECORDING = auto()
    UPLOADING = auto()
    AI_STREAMING = auto()


class Event(Enum):
    PTT_DOWN = auto()
    PTT_UP = auto()
    INPUT_STREAM_SENT = auto()
    OUTPUT_STREAM_END = auto()


class VoiceStateMachine:
    def __init__(self) -> None:
        self.state = State.IDLE

    def on_event(self, event: Event) -> None:
        if self.state == State.IDLE:
            if event == Event.PTT_DOWN:
                self.state = State.RECORDING
        elif self.state == State.RECORDING:
            if event == Event.PTT_UP:
                self.state = State.UPLOADING
        elif self.state == State.UPLOADING:
            if event == Event.INPUT_STREAM_SENT:
                self.state = State.AI_STREAMING
        elif self.state == State.AI_STREAMING:
            if event == Event.OUTPUT_STREAM_END:
                self.state = State.IDLE


class InterviewAgentSynch:
    """Synchronous, push-to-talk interview agent with streaming AI output."""

    def __init__(self) -> None:
        self.session_id = str(uuid.uuid4())
        self.audio_queue = queue.Queue()
        self.audio_buffer = bytearray()
        self.recording_buffer = bytearray()
        self.transcript_buffer = ""
        self.conversation_history = []
        self.should_end_session = False
        self.is_running = False
        self.state_machine = VoiceStateMachine()

        # PyAudio setup
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None

    def get_system_instructions(self) -> str:
        """System instructions for the Korean language tutor."""
        return """You are a friendly, casual AI Korean language interviewer. Your goal is to conduct a less than 5-minute voice-based interview in Korean to determine the user's CEFR level.

# Core Guidelines:
- Tone: Friendly, casual, and supportive—like talking to a friend.
- Language: Korean only
- Framework: Use the CEFR (A1-C1) guideline for leveling and the "Communicative Approach" for assessment.
- Method: a Semi-structured oral interview
- Topics: feel free to be creative about the topics as long as it is within the scope of the intended CEFR level

# Assessment Protocol (Scaling Difficulty):
1. Warm-up (A1): Start with very simple personal questions (e.g., name, hometown).
2. Level Up (A2-B1): Transition to open-ended questions requiring description or narration 
3. Probe the Ceiling (C1): Ask for supported opinions on abstract topics (e.g., technology in education).
IMPORTANT NOTE: avoid using complex language when asking the questions. Make sure the language used in the questions are appropriate for the intended CEFR level.
- Difficulty Scaling: Increase difficulty gradually. Do not jump abruptly from A1 to C1. 
- Termination: If the user fails to respond meaningfully after multiple attempts at a certain level, conclude the interview.

# CRITICAL ENDING INSTRUCTION:
After you provide the CEFR level assessment and say goodbye, you MUST call the end_interview function to properly terminate the session.
The function call is MANDATORY - the session will not end automatically without it.
Example flow: 1) Provide assessment ("B1 정도로 생각됩니다"), 2) Say goodbye, 3) IMMEDIATELY call end_interview function.
"""

    def get_websocket_url(self) -> str:
        """Get WebSocket URL for Realtime API."""
        return "wss://api.openai.com/v1/realtime?model=gpt-realtime"

    def get_websocket_headers(self) -> dict:
        """Get WebSocket headers for authentication."""
        api_key = os.getenv("OPENAI_API_KEY")
        return {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

    def setup_audio_streams(self) -> None:
        """Setup audio input and output streams."""
        self.input_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        self.output_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK,
            stream_callback=self.audio_output_callback,
        )

    def audio_output_callback(self, in_data, frame_count, time_info, status):
        """Playback audio from the queue."""
        bytes_needed = frame_count * BYTES_PER_SAMPLE * CHANNELS

        if len(self.audio_buffer) >= bytes_needed:
            data = bytes(self.audio_buffer[:bytes_needed])
            self.audio_buffer = self.audio_buffer[bytes_needed:]
            return (data, pyaudio.paContinue)

        try:
            while len(self.audio_buffer) < bytes_needed:
                chunk = self.audio_queue.get_nowait()
                self.audio_buffer.extend(chunk)
            data = bytes(self.audio_buffer[:bytes_needed])
            self.audio_buffer = self.audio_buffer[bytes_needed:]
            return (data, pyaudio.paContinue)
        except queue.Empty:
            return (b"\x00" * bytes_needed, pyaudio.paContinue)

    async def connect_realtime(self) -> None:
        """Connect to OpenAI Realtime API via WebSocket."""
        ws_url = self.get_websocket_url()
        headers = self.get_websocket_headers()
        header_list = [(name, value) for name, value in headers.items()]

        async with websockets.connect(ws_url, additional_headers=header_list) as websocket:
            config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": self.get_system_instructions(),
                    "voice": "marin",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1",
                        "language": "ko",
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 800,
                    },
                    "temperature": 0.8,
                    "max_response_output_tokens": 4096,
                    "tools": [
                        {
                            "type": "function",
                            "name": "end_interview",
                            "description": "MANDATORY: You MUST call this function when you have completed the interview assessment and said goodbye. This is the ONLY way to properly end the session. Call this immediately after providing the CEFR level assessment and saying farewell.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "reason": {
                                        "type": "string",
                                        "description": "Reason for ending (e.g., 'Interview completed', 'Assessment provided')",
                                    }
                                },
                                "required": ["reason"],
                            },
                        }
                    ],
                    "tool_choice": "auto",
                    "tracing": {
                        "workflow_name": "korean_voice_tutor_interview",
                        "group_id": self.session_id,
                        "metadata": {
                            "application": "Korean Voice Tutor",
                            "session_type": "language_assessment",
                            "language": "korean",
                            "cefr_assessment": "true",
                            "session_start_time": datetime.now().isoformat(),
                            "tools_enabled": "end_interview",
                        },
                    },
                },
            }

            await websocket.send(json.dumps(config))
            print("✅ Configuration sent")
            print(f"📊 Session ID: {self.session_id}")

            event_task = asyncio.create_task(self.event_handler(websocket))
            ptt_task = asyncio.create_task(self.ptt_handler(websocket))
            recording_task = asyncio.create_task(self.recording_loop())

            try:
                await asyncio.gather(event_task, ptt_task, recording_task)
            finally:
                event_task.cancel()
                ptt_task.cancel()
                recording_task.cancel()
                await asyncio.gather(
                    event_task, ptt_task, recording_task, return_exceptions=True
                )

    async def recording_loop(self) -> None:
        """Capture audio while in RECORDING state."""
        while self.is_running and not self.should_end_session:
            if self.state_machine.state == State.RECORDING:
                data = self.input_stream.read(CHUNK, exception_on_overflow=False)
                self.recording_buffer.extend(data)
            else:
                await asyncio.sleep(0.01)

    async def ptt_handler(self, websocket) -> None:
        """Push-to-talk handler using SPACE toggle and ESC to quit (Windows)."""
        print("\n🎙️ Press SPACE to start/stop recording. Press ESC to quit.")
        if os.name != "nt":
            raise RuntimeError("SHIFT/ESC key polling requires Windows.")

        while self.is_running and not self.should_end_session:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b"\x1b":  # ESC
                    self.should_end_session = True
                    self.is_running = False
                    break
                if key == b" ":  # SPACE
                    if self.state_machine.state == State.IDLE:
                        self.state_machine.on_event(Event.PTT_DOWN)
                        self.recording_buffer = bytearray()
                        print("🔴 Recording...")
                    elif self.state_machine.state == State.RECORDING:
                        self.state_machine.on_event(Event.PTT_UP)
                        print("🟡 Uploading...")
                        await self.send_recording(websocket)
                    else:
                        # No barge-in while AI is speaking or uploading.
                        print("⏳ Please wait for the AI to finish.")

            await asyncio.sleep(0.01)

    async def send_recording(self, websocket) -> None:
        """Send recorded audio to the API and request a response."""
        if not self.recording_buffer:
            self.state_machine.on_event(Event.OUTPUT_STREAM_END)
            print("⚠️ No audio captured.")
            return

        await websocket.send(json.dumps({"type": "input_audio_buffer.clear"}))

        chunk_size = CHUNK * BYTES_PER_SAMPLE * CHANNELS
        for offset in range(0, len(self.recording_buffer), chunk_size):
            chunk = self.recording_buffer[offset : offset + chunk_size]
            await websocket.send(
                json.dumps(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode("utf-8"),
                    }
                )
            )

        await websocket.send(json.dumps({"type": "input_audio_buffer.commit"}))
        await websocket.send(
            json.dumps(
                {
                    "type": "response.create",
                    "response": {"modalities": ["audio", "text"]},
                }
            )
        )
        self.state_machine.on_event(Event.INPUT_STREAM_SENT)
        self.recording_buffer = bytearray()
        print("🔵 AI responding...")

    async def wait_for_playback_drain(self) -> None:
        """Wait until the audio queue and buffer are drained."""
        while self.audio_queue.qsize() > 0 or len(self.audio_buffer) > 0:
            await asyncio.sleep(0.05)

    async def event_handler(self, websocket) -> None:
        """Handle events from the API."""
        async for message in websocket:
            event = json.loads(message)
            event_type = event.get("type")

            if event_type == "response.audio_transcript.delta":
                delta = event.get("delta", "")
                if delta:
                    self.transcript_buffer += delta

            elif event_type == "response.audio_transcript.done":
                if self.transcript_buffer:
                    ai_text = self.transcript_buffer
                    print(f"🤖 AI: {ai_text}")
                    self.conversation_history.append(("AI", ai_text))
                    self.transcript_buffer = ""

            elif event_type == "response.audio.delta":
                audio_data = event.get("delta", "")
                if audio_data:
                    audio_bytes = base64.b64decode(audio_data)
                    if len(audio_bytes) % 2 != 0:
                        audio_bytes += b"\x00"
                    self.audio_queue.put(audio_bytes)

            elif event_type == "conversation.item.input_audio_transcription.completed":
                transcript = event.get("transcript", "")
                print(f"👤 You: {transcript}")
                self.conversation_history.append(("User", transcript))

            elif event_type == "response.function_call_arguments.done":
                function_call = event.get("function_call", {}) or event.get(
                    "function_call_arguments", {}
                )
                function_name = function_call.get("name", "")
                if function_name == "end_interview":
                    arguments = function_call.get("arguments", {})
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except (json.JSONDecodeError, ValueError):
                            arguments = {}
                    reason = (
                        arguments.get("reason", "Interview completed")
                        if isinstance(arguments, dict)
                        else "Interview completed"
                    )
                    print(f"\n👋 Interview ending: {reason}")
                    self.should_end_session = True
                    self.is_running = False
                    break

            elif event_type == "response.done":
                await self.wait_for_playback_drain()
                self.state_machine.on_event(Event.OUTPUT_STREAM_END)
                print("✅ Response complete. Ready for next turn.")

            elif event_type == "error":
                error = event.get("error", {})
                print(f"❌ API Error: {error.get('message', 'Unknown error')}")

    async def run(self) -> None:
        """Main run loop."""
        try:
            print("🇰🇷 Korean Voice Tutor (Sync Mode) Starting...")
            print("=" * 50)
            self.setup_audio_streams()
            self.input_stream.start_stream()
            self.output_stream.start_stream()
            self.is_running = True
            await self.connect_realtime()
        except KeyboardInterrupt:
            print("\n\n👋 Stopping Korean Voice Tutor...")
        except Exception as exc:
            print(f"\n❌ Error: {exc}")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Clean up resources."""
        self.is_running = False
        self.should_end_session = False
        self.transcript_buffer = ""
        self.recording_buffer = bytearray()

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
        """Get the conversation history for assessment."""
        return self.conversation_history.copy()
