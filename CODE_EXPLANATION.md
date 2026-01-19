# Detailed Step-by-Step Code Explanation: Korean Voice Tutor

This document provides a comprehensive breakdown of how the audio conversation system works in `app.py`, from initialization to completion.

---

## 📋 Table of Contents

1. [Initialization Phase](#1-initialization-phase)
2. [Audio Configuration](#2-audio-configuration)
3. [Audio Stream Setup](#3-audio-stream-setup)
4. [WebSocket Connection](#4-websocket-connection)
5. [Session Configuration](#5-session-configuration)
6. [Audio Input Flow](#6-audio-input-flow)
7. [Audio Output Flow](#7-audio-output-flow)
8. [Event Handling](#8-event-handling)
9. [Cleanup Phase](#9-cleanup-phase)

---

## 1. Initialization Phase

### Step 1.1: Module Imports (Lines 11-20)
```python
import os, asyncio, json
from openai import OpenAI
from dotenv import load_dotenv
import websockets, base64, pyaudio, threading, queue
```

**Purpose:**
- `os`: Access environment variables
- `asyncio`: Handle asynchronous operations (WebSocket, audio streaming)
- `json`: Parse WebSocket messages
- `OpenAI`: OpenAI SDK client
- `websockets`: WebSocket client for real-time communication
- `pyaudio`: Audio I/O (microphone input, speaker output)
- `base64`: Encode/decode audio data for transmission
- `queue`: Thread-safe queue for audio data

### Step 1.2: Environment Setup (Line 23)
```python
load_dotenv()
```
**Purpose:** Loads API key from `.env` file into environment variables.

### Step 1.3: Audio Constants (Lines 25-30)
```python
CHUNK = 1024          # Frames per buffer
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHANNELS = 1          # Mono audio
RATE = 24000          # 24kHz sample rate
BYTES_PER_SAMPLE = 2  # 16-bit = 2 bytes
```

**Purpose:** Defines audio format matching OpenAI Realtime API requirements:
- **CHUNK**: Number of audio frames processed at once (1024 frames)
- **FORMAT**: 16-bit PCM (Pulse Code Modulation) - uncompressed audio
- **CHANNELS**: Mono (1 channel) - single audio stream
- **RATE**: 24,000 Hz - samples per second (OpenAI's requirement)
- **BYTES_PER_SAMPLE**: 2 bytes per sample (16 bits ÷ 8)

**Why these values?**
- OpenAI Realtime API expects PCM16 at 24kHz
- 1024 frames = ~42ms of audio at 24kHz (good balance between latency and stability)

---

## 2. Initialization Phase: KoreanVoiceTutor Class

### Step 2.1: Class Initialization (Lines 32-46)
```python
def __init__(self):
    self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    self.session_id = None
    self.audio_queue = queue.Queue()
    self.audio_buffer = bytearray()
    self.is_running = False
    self.audio = pyaudio.PyAudio()
    self.input_stream = None
    self.output_stream = None
```

**Purpose:** Initializes all components:
- **`client`**: OpenAI API client (for future use, not directly used for Realtime)
- **`audio_queue`**: Thread-safe queue storing decoded audio chunks from API
- **`audio_buffer`**: Temporary buffer for handling variable-sized audio chunks
- **`is_running`**: Flag to control async loops
- **`audio`**: PyAudio instance (manages audio devices)
- **`input_stream`**: Microphone input stream (not yet opened)
- **`output_stream`**: Speaker output stream (not yet opened)

---

## 3. Audio Stream Setup

### Step 3.1: Setup Audio Streams (Lines 75-101)
```python
def setup_audio_streams(self):
    # Input stream (microphone)
    self.input_stream = self.audio.open(
        format=FORMAT,        # 16-bit PCM
        channels=CHANNELS,    # Mono (1 channel)
        rate=RATE,            # 24kHz
        input=True,            # Input device
        frames_per_buffer=CHUNK  # 1024 frames
    )
    
    # Output stream (speakers)
    self.output_stream = self.audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        output=True,          # Output device
        frames_per_buffer=CHUNK,
        stream_callback=self.audio_output_callback  # Callback function
    )
```

**Purpose:** Opens two audio streams:

**Input Stream (Microphone):**
- Reads audio from default microphone
- Format: 16-bit PCM, mono, 24kHz
- Reads 1024 frames at a time (~42ms chunks)
- **No callback** - we'll read directly in async loop using `input_stream.read()`

**Output Stream (Speakers):**
- Plays audio to default speakers/headphones
- Same format as input
- **Uses callback** - PyAudio calls `audio_output_callback` when it needs audio data
- This allows real-time playback without blocking

**What is a "callback"?**
A **callback** is a function that gets called automatically by PyAudio when something happens:
- **For output**: PyAudio calls `audio_output_callback()` whenever its audio buffer is running low and needs more data to play
- **For input (not used here)**: PyAudio could call a callback whenever new audio data is available from the microphone

**Why no callback for input?**
- We control when to read: `input_stream.read(CHUNK)` in our async loop
- Gives us more control over timing and when to send data to the API
- Simpler to integrate with our WebSocket sending logic

**Why callback for output?**
- PyAudio needs audio data continuously and on-demand
- Callback is called automatically when buffer needs refilling
- Ensures smooth, uninterrupted playback without us having to constantly check
- PyAudio handles the timing - we just provide data when asked

---

## 4. Audio Output Callback

### Step 4.1: Callback Function (Lines 103-126)
```python
def audio_output_callback(self, in_data, frame_count, time_info, status):
    bytes_needed = frame_count * BYTES_PER_SAMPLE * CHANNELS
    # Returns exactly the bytes PyAudio needs
```

**How it works:**

1. **PyAudio requests audio** (e.g., "I need 1024 frames of audio")
2. **Calculate bytes needed**: `1024 frames × 2 bytes × 1 channel = 2048 bytes`
3. **Check buffer first**: If `audio_buffer` has enough data, use it
4. **If not enough**: Pull chunks from `audio_queue` until buffer is full
5. **Return audio data**: PyAudio plays it immediately
6. **If queue empty**: Return silence (zeros) to prevent audio glitches

**Flow Diagram:**
```
API sends audio → event_handler → audio_queue → audio_buffer → callback → speakers
```

**Why the buffer?**
- API sends variable-sized chunks (might be 500 bytes, 2000 bytes, etc.)
- PyAudio needs exact sizes (e.g., 2048 bytes)
- Buffer accumulates chunks until we have enough, then returns exact amount

---

## Alternative: Using Frameworks to Reduce Boilerplate

**Yes, there are frameworks that can simplify this!** The current implementation uses manual WebSocket handling, but you can reduce boilerplate in two ways:

### Option 1: OpenAI Python SDK's `beta.realtime.connect` (Recommended)

OpenAI's official Python SDK (v1.61.0+) includes `beta.realtime.connect()`, which provides a higher-level abstraction that eliminates:
- Manual WebSocket connection management
- Manual JSON event serialization/deserialization  
- Manual header construction
- Manual base64 encoding/decoding (for some operations)

**Example using the SDK:**
```python
from openai import AsyncOpenAI

async with AsyncOpenAI().beta.realtime.connect(model="gpt-realtime") as connection:
    await connection.session.update(session={
        'modalities': ['audio', 'text'],
        'voice': 'marin',
        # ... other config
    })
    
    # Send events using method calls instead of raw JSON
    await connection.input_audio_buffer.append(audio=data)
    
    # Receive events as typed objects
    async for event in connection:
        if event.type == 'response.audio.delta':
            audio_bytes = event.delta  # Already decoded!
            self.audio_queue.put(audio_bytes)
```

**What it doesn't handle:**
- Audio streaming I/O (PyAudio queues/buffers) - still needed
- Real-time microphone capture and speaker playback
- Audio format conversion/buffering for PyAudio callbacks

**Trade-offs:**
- ✅ Cleaner, more maintainable API code
- ✅ Type safety and better error handling
- ✅ Automatic retry/reconnection logic
- ⚠️ Still need to handle audio I/O buffers manually

### Option 2: Community Wrapper Libraries

Several community projects wrap the Realtime API further:
- **openai-realtime-py**: Additional abstractions for event handling
- **OpenAI Realtime Python API**: More structured client with helper methods

### Option 3: Audio Streaming Frameworks

For the audio I/O side, you could use:
- **pyaudio_helper**: Wraps PyAudio with `DSPIOStream` for cleaner callback handling
- **sounddevice**: Higher-level audio library with simpler async interfaces

**Note:** Even with frameworks, the core audio buffering logic (queue → buffer → callback) is typically still needed because:
1. WebSocket streams are async/asynchronous
2. PyAudio callbacks are synchronous and blocking
3. API chunks don't match PyAudio frame requirements

The frameworks mainly help with the **WebSocket/API communication layer**, not the **audio I/O layer**.

---

## 5. WebSocket Connection

### Step 5.1: Get Connection Details (Lines 61-73)
```python
def get_websocket_url(self):
    return "wss://api.openai.com/v1/realtime?model=gpt-realtime"

def get_websocket_headers(self):
    return {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "realtime=v1"
    }
```

**Purpose:**
- **URL**: WebSocket endpoint with model specification
- **Headers**: Authentication (API key) and beta API flag

### Step 5.2: Establish Connection (Lines 128-177)
```python
async def connect_realtime(self):
    ws_url = self.get_websocket_url()
    headers = self.get_websocket_headers()
    header_list = [(name, value) for name, value in headers.items()]
    
    async with websockets.connect(ws_url, additional_headers=header_list) as websocket:
        # Connection established!
```

**What happens:**
1. Creates WebSocket connection to OpenAI
2. Sends authentication headers
3. Connection stays open for bidirectional communication
4. `async with` ensures proper cleanup on exit

---

## 5A. Alternative: WebRTC Connection (January 2026 Update)

**Important Update:** As of January 2026, OpenAI's Realtime API now supports **WebRTC natively** alongside WebSocket! This is a significant update that offers lower latency and better audio optimization.

### WebRTC vs WebSocket Comparison

| Factor | WebSocket (Current) | WebRTC (Available) |
|--------|---------------------|-------------------|
| **Latency** | 100-300ms typical | 50-100ms typical |
| **Audio Optimization** | ❌ Manual handling | ✅ Built-in (codecs, jitter buffering) |
| **Base64 Encoding** | ✅ Required (text-based) | ❌ Not needed (binary) |
| **Code Complexity** | Low (~50 lines) | Medium-High (~150+ lines) |
| **Python Support** | Excellent (`websockets`) | Good (`aiortc` library) |
| **Connection Setup** | Simple (direct connect) | Complex (SDP offer/answer) |
| **NAT/Firewall** | Usually works | May need TURN servers |
| **Best For** | Server-side, simple apps | Browser apps, low-latency needs |

### WebRTC Implementation Overview

**Using OpenAI SDK with WebRTC:**
```python
from openai import AsyncOpenAI
from aiortc import RTCPeerConnection, RTCSessionDescription

async def connect_realtime_webrtc(self):
    client = AsyncOpenAI()
    
    # Create WebRTC peer connection
    pc = RTCPeerConnection()
    
    # Create SDP offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    
    # Send offer to OpenAI API
    response = await client.beta.realtime.calls.create(
        sdp_offer=offer.sdp,
        model="gpt-realtime"
    )
    
    # Set remote description with OpenAI's answer
    answer = RTCSessionDescription(
        sdp=response.sdp_answer,
        type="answer"
    )
    await pc.setRemoteDescription(answer)
    
    # Handle audio tracks
    @pc.on("track")
    async def on_track(track):
        if track.kind == "audio":
            # Receive audio directly (no base64 decoding needed!)
            async for frame in track:
                audio_data = frame.to_ndarray()
                # Process audio...
```

**Key Advantages of WebRTC:**
1. **Lower Latency**: 50-100ms vs 100-300ms for WebSocket
2. **No Base64 Encoding**: Direct binary audio transmission
3. **Built-in Audio Processing**: Automatic codec handling, jitter buffering
4. **Better Quality**: Adaptive bitrate, congestion control
5. **Native Browser Support**: Perfect for web applications

**Key Disadvantages:**
1. **More Complex Setup**: Requires SDP offer/answer exchange
2. **Still Need Buffering**: PyAudio callback synchronization still required
3. **NAT/Firewall Issues**: May need TURN servers in some networks
4. **Less Mature Python Support**: `aiortc` is less established than `websockets`

### When to Use WebRTC vs WebSocket

**Use WebRTC if:**
- ✅ Building a browser-based application
- ✅ Latency is critical (<100ms needed)
- ✅ You want built-in audio optimization
- ✅ You're comfortable with WebRTC complexity

**Stick with WebSocket if:**
- ✅ Building a simple server-side Python app (like this one)
- ✅ Current latency is acceptable
- ✅ You want simpler, more maintainable code
- ✅ You're behind strict firewalls/NATs

### Current Implementation Choice

This codebase uses **WebSocket** because:
- Simpler implementation for a Python desktop app
- No browser-specific requirements
- Easier to debug and maintain
- Current latency is acceptable for language learning

**Note:** You could migrate to WebRTC for better latency, but you'd still need the audio queue/buffer logic for PyAudio callbacks.

---

## 6. Session Configuration

### Step 6.1: Send Session Config (Lines 142-165)
```python
config = {
    "type": "session.update",
    "session": {
        "modalities": ["text", "audio"],  # We want both text and audio
        "instructions": self.get_system_instructions(),  # Korean tutor prompt
        "voice": "marin",  # AI voice selection
        "input_audio_format": "pcm16",   # Our mic format
        "output_audio_format": "pcm16",  # AI response format
        "input_audio_transcription": {
            "model": "whisper-1"  # Transcribe our speech to text
        },
        "turn_detection": {
            "type": "server_vad",  # Voice Activity Detection on server
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500
        },
        "temperature": 0.8,
        "max_response_output_tokens": 4096
    }
}
await websocket.send(json.dumps(config))
```

**Key Settings Explained:**

**Modalities:**
- `["text", "audio"]`: We get both text transcripts and audio
- Text helps with debugging, audio for playback

**Voice:**
- `"marin"`: One of OpenAI's voice options
- Others: `cedar`, `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

**Turn Detection:**
- `server_vad`: Server detects when you stop speaking
- `threshold: 0.5`: Sensitivity (0.0-1.0)
- `silence_duration_ms: 500`: Wait 500ms of silence before processing
- `prefix_padding_ms: 300`: Include 300ms before speech starts

**Why turn detection?**
- Prevents cutting off mid-sentence
- Waits for natural pauses
- Handles interruptions gracefully

---

## 7. Audio Input Flow (Microphone → API)

### Step 7.1: Audio Input Handler (Lines 179-196)
```python
async def audio_input_handler(self, websocket):
    while self.is_running:
        # Read audio from microphone
        data = self.input_stream.read(CHUNK, exception_on_overflow=False)
        
        # Encode to base64
        audio_event = {
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(data).decode('utf-8')
        }
        
        # Send to API
        await websocket.send(json.dumps(audio_event))
        
        await asyncio.sleep(0.01)  # Small delay
```

**Step-by-Step Flow:**

1. **Read from microphone**: `input_stream.read(CHUNK)` gets 1024 frames (~2048 bytes)
2. **Encode to base64**: API expects base64-encoded strings (not raw bytes)
3. **Create event**: Format as `input_audio_buffer.append` event
4. **Send via WebSocket**: Transmit to OpenAI API
5. **Small delay**: Prevents overwhelming the connection (10ms pause)

**Why base64?**
- WebSocket messages are text-based
- Binary audio data needs encoding
- Base64 is standard for this

**Continuous Loop:**
- Runs as long as `is_running = True`
- Sends audio chunks continuously (~100 times per second)
- API accumulates chunks until turn detection triggers processing

---

## 8. Audio Output Flow (API → Speakers)

### Step 8.1: Event Handler (Lines 208-263)
```python
async def event_handler(self, websocket):
    async for message in websocket:
        event = json.loads(message)
        event_type = event.get("type")
        
        if event_type == "response.audio.delta":
            audio_data = event.get("delta", "")
            audio_bytes = base64.b64decode(audio_data)
            self.audio_queue.put(audio_bytes)
```

**Step-by-Step Flow:**

1. **Receive WebSocket message**: API sends JSON event
2. **Parse event type**: Check what kind of event it is
3. **Handle audio delta**: When `response.audio.delta` received:
   - Extract base64 audio string
   - Decode to raw bytes (PCM16)
   - Validate length (must be even for 16-bit)
   - Add to `audio_queue`
4. **Callback picks it up**: `audio_output_callback` pulls from queue and plays

**Event Types Handled:**

| Event Type | Purpose |
|------------|---------|
| `session.created` | Session initialized |
| `session.updated` | Configuration applied |
| `response.audio_transcript.delta` | Text of what AI is saying (for display) |
| `response.audio_transcript.done` | Transcript complete |
| `response.audio.delta` | **Audio chunks for playback** |
| `conversation.item.input_audio_transcription.completed` | Your speech transcribed |
| `response.done` | AI finished responding |
| `error` | Error occurred |

**Why delta events?**
- Audio comes in chunks (streaming)
- Each `delta` is a piece of the full response
- We accumulate chunks in queue for smooth playback

---

## 9. Main Execution Flow

### Step 9.1: Run Method (Lines 265-293)
```python
async def run(self):
    # 1. Setup audio streams
    self.setup_audio_streams()
    
    # 2. Start audio streams
    self.input_stream.start_stream()
    self.output_stream.start_stream()
    
    # 3. Set running flag
    self.is_running = True
    
    # 4. Connect to API
    await self.connect_realtime()
```

**Execution Order:**

1. **Setup audio**: Opens microphone and speaker streams
2. **Start streams**: Begins capturing/playing audio
3. **Connect API**: Establishes WebSocket connection
4. **Start tasks**: Three async tasks run concurrently:
   - `audio_input_handler`: Sends mic audio to API
   - `audio_output_handler`: Placeholder (audio handled by callback)
   - `event_handler`: Receives and processes API events

**Concurrent Execution:**
```
┌─────────────────────────────────────┐
│  Main Thread (asyncio.run)          │
├─────────────────────────────────────┤
│  ┌──────────────────────────────┐   │
│  │ audio_input_handler          │   │
│  │ (sends mic → API)            │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │ event_handler                │   │
│  │ (receives API → queue)       │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │ audio_output_callback        │   │
│  │ (queue → speakers)           │   │
│  │ (called by PyAudio)          │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

---

## 10. Complete Conversation Flow

### Example: User says "안녕하세요" (Hello)

**Step 1: User speaks**
```
Microphone → input_stream.read() → base64 encode → WebSocket → API
```

**Step 2: API processes**
```
API receives audio chunks → Voice Activity Detection → 
Wait for silence (500ms) → Process with Whisper → 
Generate Korean response → Convert to audio
```

**Step 3: API responds**
```
API → WebSocket events:
  - response.audio_transcript.delta: "안녕하세요! 반갑습니다."
  - response.audio.delta: [base64 audio chunk 1]
  - response.audio.delta: [base64 audio chunk 2]
  - ...
  - response.audio.delta: [base64 audio chunk N]
  - response.done
```

**Step 4: Playback**
```
event_handler receives deltas → 
Decode base64 → audio_queue.put() → 
audio_output_callback pulls from queue → 
audio_buffer accumulates → 
Returns exact bytes to PyAudio → 
Speakers play audio
```

**Timeline:**
```
0ms:    User starts speaking
500ms:  User finishes, silence detected
600ms:  API starts processing
1200ms: API sends first audio chunk
1201ms: Chunk decoded, added to queue
1202ms: Callback pulls chunk, plays audio
...     More chunks arrive and play
2500ms: Response complete
```

---

## 11. Cleanup Phase

### Step 11.1: Cleanup Method (Lines 295-310)
```python
def cleanup(self):
    self.is_running = False  # Stops all loops
    
    if self.input_stream:
        self.input_stream.stop_stream()
        self.input_stream.close()
    
    if self.output_stream:
        self.output_stream.stop_stream()
        self.output_stream.close()
    
    if self.audio:
        self.audio.terminate()  # Closes PyAudio
```

**What happens:**
1. **Set flag**: `is_running = False` stops all async loops
2. **Stop streams**: Prevents further audio I/O
3. **Close streams**: Releases audio device resources
4. **Terminate PyAudio**: Closes PyAudio library

**Why cleanup?**
- Prevents resource leaks
- Releases microphone/speaker for other apps
- Ensures graceful shutdown

---

## 12. Entry Point

### Step 12.1: Main Function (Lines 313-327)
```python
async def main():
    tutor = KoreanVoiceTutor()
    await tutor.run()

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found")
        exit(1)
    
    asyncio.run(main())
```

**Execution:**
1. **Check API key**: Validates environment variable exists
2. **Create tutor**: Instantiates `KoreanVoiceTutor` class
3. **Run**: Starts the async event loop
4. **Handle interrupts**: Ctrl+C triggers cleanup

---

## 🔄 Complete Data Flow Summary

```
┌─────────────┐
│  Microphone │
└──────┬──────┘
       │ (PCM16, 24kHz, mono)
       ▼
┌──────────────────┐
│ input_stream     │
│ (PyAudio)        │
└──────┬───────────┘
       │ (1024 frames/chunk)
       ▼
┌──────────────────┐
│ base64 encode    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ WebSocket        │
│ (to OpenAI API)  │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ OpenAI Realtime  │
│ API Processing   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ WebSocket        │
│ (from API)       │
└──────┬───────────┘
       │ (response.audio.delta events)
       ▼
┌──────────────────┐
│ base64 decode    │
└──────┬───────────┘
       │ (PCM16 bytes)
       ▼
┌──────────────────┐
│ audio_queue      │
│ (thread-safe)    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ audio_buffer     │
│ (accumulates)    │
└──────┬───────────┘
       │ (exact bytes needed)
       ▼
┌──────────────────┐
│ output_stream    │
│ (PyAudio)        │
└──────┬───────────┘
       │ (PCM16, 24kHz, mono)
       ▼
┌─────────────┐
│  Speakers   │
└─────────────┘
```

---

## 🎯 Key Concepts

### Asynchronous Programming
- **Why async?** Audio I/O and network operations are I/O-bound
- **Non-blocking**: Can handle multiple operations simultaneously
- **Tasks**: Three concurrent tasks handle input, output, and events

### Audio Buffering
- **Queue**: Thread-safe storage for audio chunks
- **Buffer**: Accumulates variable-sized chunks into exact sizes
- **Prevents glitches**: Always has data ready when PyAudio needs it

### WebSocket Protocol
- **Bidirectional**: Send and receive simultaneously
- **Real-time**: Low latency for voice conversations
- **Event-based**: Different event types for different data

### Turn Detection
- **VAD**: Voice Activity Detection knows when you're speaking
- **Silence detection**: Waits for natural pauses
- **Prevents cut-off**: Includes padding before/after speech

---

## 🐛 Common Issues & Solutions

### Issue: Broken/Distorted Audio
**Causes:**
- Buffer underrun (queue empty when callback needs data)
- Incorrect byte alignment (odd-length chunks)
- Sample rate mismatch

**Solutions:**
- Audio buffer accumulates chunks
- Padding for odd-length data
- Exact format matching (24kHz, PCM16, mono)

### Issue: No Audio Output
**Causes:**
- Queue not receiving data
- Callback not being called
- Audio device not available

**Solutions:**
- Check `event_handler` is receiving `response.audio.delta`
- Verify `audio_queue` has items
- Check audio device permissions

### Issue: High Latency
**Causes:**
- Large buffer sizes
- Network delay
- Processing time

**Solutions:**
- CHUNK size (1024) balances latency/stability
- Turn detection settings affect response time
- API processing is server-side (unavoidable)

---

## 📚 Additional Resources

- [OpenAI Realtime API Docs](https://platform.openai.com/docs/guides/realtime)
- [PyAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/docs/)
- [Python asyncio Guide](https://docs.python.org/3/library/asyncio.html)
- [WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)

---

This completes the detailed explanation of the Korean Voice Tutor audio conversation system!
