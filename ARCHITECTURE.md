# Korean Voice Tutor - Architecture Overview

## Project Structure

```
korean_voice_tutor/
│
├── core/                          # 🔷 SHARED: Core business logic
│   ├── __init__.py
│   ├── assessment_agent.py        # Assessment generation
│   ├── assessment_state_machine.py # Assessment flow control
│   └── tools/                     # Interview protocols & guidance
│       ├── __init__.py
│       ├── interview_guidance.py
│       └── assessment_guidance.py
│
├── desktop/                       # 🖥️ DESKTOP: PyAudio-based app
│   ├── audio/                     # PyAudio I/O
│   ├── session/                   # Desktop session management
│   ├── handlers/                  # Event handlers
│   ├── websocket/                 # Event dispatcher
│   ├── interview_agent_v2.py      # Desktop orchestrator
│   └── app_v2.py                  # Desktop entry point
│
├── web/                           # 🌐 WEB: Browser-based app
│   ├── backend/                   # FastAPI server
│   │   ├── server.py              # Main FastAPI app
│   │   ├── realtime_bridge.py     # OpenAI bridge
│   │   ├── session_store.py       # Multi-user sessions
│   │   └── requirements.txt
│   │
│   ├── frontend/                  # Browser client
│   │   ├── index.html             # UI
│   │   ├── app.js                 # PTT logic
│   │   ├── audio.js               # Browser audio
│   │   └── style.css
│   │
│   ├── Dockerfile                 # HuggingFace deployment
│   └── README.md
│
├── reports/                       # 💾 Assessment reports (generated)
├── tools/                         # 📚 Original tools (kept for reference)
└── interview_agent.py             # 📜 Original (kept for reference)
```

## Architecture Layers

### Layer 1: Core (Shared)

**Purpose:** Reusable business logic for both desktop and web

**Components:**
- `AssessmentAgent` - Generates CEFR proficiency reports
- `AssessmentStateMachine` - Manages assessment delivery flow
- `tools/` - Interview protocols and guidance

**Used by:** Desktop and Web versions

### Layer 2a: Desktop Interface

**Purpose:** Local desktop application with PyAudio

**Flow:**
```
Microphone → PyAudio → InterviewAgent → OpenAI Realtime API
                ↓                              ↓
            Speakers ← AudioManager ← Response Events
```

**Key Features:**
- Continuous bidirectional streaming
- Server VAD (Voice Activity Detection)
- Direct PyAudio I/O
- Single user

### Layer 2b: Web Interface

**Purpose:** Browser-based application with PTT

**Flow:**
```
Browser → MediaRecorder → WebSocket → FastAPI → OpenAI Realtime API
                                         ↓              ↓
        Web Audio API ← WebSocket ← FastAPI ← Response Events
```

**Key Features:**
- Push-to-Talk (PTT) interface
- Manual turn-taking
- Multi-user support
- Mobile-optimized
- Cloud-deployable

## Communication Protocols

### Desktop → OpenAI

```
Desktop App → Direct WebSocket → OpenAI Realtime API
- Streaming audio input
- Server VAD enabled
- Continuous conversation
```

### Web → OpenAI

```
Browser → WebSocket → FastAPI → WebSocket → OpenAI Realtime API
- Discrete audio messages (PTT)
- Manual turn-taking (no VAD)
- Server-side bridging
```

## Audio Handling Comparison

### Desktop (Continuous Streaming)

```python
# PyAudio reads continuously
while True:
    chunk = stream.read(CHUNK)
    # Send to OpenAI immediately
    send_audio(chunk)
```

**Advantages:**
- Natural conversation flow
- Low latency
- Can interrupt

### Web (PTT Messages)

```javascript
// Record while button pressed
onButtonPress() {
    recorder.start();
}

onButtonRelease() {
    recorder.stop();
    // Send complete message
    sendAudio(audioBlob);
}
```

**Advantages:**
- Better for mobile
- Clearer turn-taking
- Reduced background noise
- Works in any browser

## State Management

### Desktop Session

```python
class SessionManager:
    - conversation_history
    - session_flags
    - function_tracking
    - single_user_state
```

### Web Session Store

```python
class UserSession:
    - per_user_state
    - conversation_history
    - openai_connection
    
class SessionStore:
    - multiple_sessions: {user_id: UserSession}
    - cleanup_stale_sessions()
```

## Assessment Flow (Shared)

Both desktop and web use the same core assessment logic:

```
1. Interview proceeds normally
2. AI detects linguistic ceiling
3. trigger_assessment() called
4. AssessmentStateMachine triggered
5. AI acknowledges: "평가를 준비하고 있습니다..."
6. AssessmentAgent generates report
7. Verbal summary created
8. AI speaks summary
9. Goodbye message
10. Session ends
```

## Deployment Options

### Desktop

```bash
cd desktop
python app_v2.py
```

**Requirements:**
- Python 3.9+
- PyAudio
- Local microphone/speakers
- Windows/Mac/Linux

### Web (Local)

```bash
cd web/backend
python server.py
```

**Requirements:**
- Python 3.9+
- FastAPI, uvicorn
- Modern browser
- Any OS with Python

### Web (HuggingFace)

```bash
# Upload web/ folder to HuggingFace Spaces
# Set OPENAI_API_KEY secret
# Dockerfile auto-deploys
```

**Requirements:**
- HuggingFace account
- OpenAI API key
- Docker (automatic)

## Code Reuse

### Shared Components (100% reuse)

- ✅ `assessment_agent.py` - Assessment generation
- ✅ `assessment_state_machine.py` - Flow control
- ✅ `tools/` - Interview protocols

### Platform-Specific

Desktop:
- `audio/` - PyAudio implementation
- `interview_agent_v2.py` - Desktop orchestrator

Web:
- `backend/` - FastAPI server
- `frontend/` - Browser client

## Benefits of Shared Core

1. **Consistency**
   - Same assessment logic everywhere
   - Same interview protocol
   - Same report format

2. **Maintainability**
   - Fix bugs once
   - Update protocol once
   - Test core once

3. **Extensibility**
   - Easy to add new interfaces (mobile app, API)
   - Core logic stays stable
   - Platform-specific optimizations

## Migration Path

### Phase 1: Current State ✅
- Core extracted and shared
- Desktop refactored and working
- Web version implemented

### Phase 2: Testing
- Test desktop version thoroughly
- Test web version thoroughly
- Verify core logic consistency

### Phase 3: Deployment
- Deploy desktop as standalone
- Deploy web to HuggingFace
- Monitor both in production

### Phase 4: Future Enhancements
- Add mobile native app (shares core)
- Add REST API (shares core)
- Add analytics dashboard

## Development Workflow

### Working on Core Logic

```bash
# Edit core/assessment_agent.py
# Both desktop and web automatically benefit
```

### Working on Desktop

```bash
cd desktop
python app_v2.py
# Only desktop affected
```

### Working on Web

```bash
cd web/backend
python server.py
# Only web affected
```

## Testing Strategy

### Core Tests
```bash
# Test shared assessment logic
python -m pytest core/
```

### Desktop Tests
```bash
# Test desktop-specific components
python -m pytest desktop/
```

### Web Tests
```bash
# Test backend
python -m pytest web/backend/

# Test frontend (manual)
open http://localhost:7860
```

## Performance Characteristics

### Desktop
- **Latency:** 50-200ms (local audio)
- **Throughput:** Real-time streaming
- **Resource:** ~100MB RAM, 1 CPU core

### Web
- **Latency:** 200-500ms (network + encoding)
- **Throughput:** 50+ concurrent users
- **Resource:** ~500MB RAM for 10 users

## Security Considerations

### Desktop
- API key stored in .env (local)
- No network exposure
- Single user

### Web
- API key on server only
- Session isolation
- Rate limiting recommended
- HTTPS required for production

## Future Architecture

### Potential Additions

```
korean_voice_tutor/
├── core/                   # Shared (existing)
├── desktop/                # Desktop (existing)
├── web/                    # Web (existing)
├── mobile/                 # Native iOS/Android app
│   └── uses core/
├── api/                    # REST API for integrations
│   └── uses core/
└── analytics/              # Usage analytics dashboard
    └── uses core/ data
```

All share the same core assessment logic! 🎯
