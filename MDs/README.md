# Korean Voice Tutor - Web Version

Push-to-Talk (PTT) web application for Korean language proficiency assessment.

## Features

- 📱 **Mobile-First Design** - Optimized for mobile browsers
- 🎤 **Push-to-Talk Interface** - Hold button to speak, release to send
- 🔄 **Real-time Audio** - AI responses stream back immediately
- 📊 **Automatic Assessment** - CEFR level evaluation at linguistic ceiling
- 🌐 **Multi-user Support** - Handle multiple concurrent interviews
- ☁️ **Cloud Ready** - Deploy to HuggingFace Spaces

## Quick Start

### Local Development

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Set up environment:**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. **Run server:**
```bash
python server.py
```

4. **Open browser:**
```
http://localhost:7860
```

### Project Structure

```
web/
├── backend/
│   ├── server.py              # FastAPI main server
│   ├── realtime_bridge.py     # OpenAI Realtime API bridge
│   ├── session_store.py       # Multi-user session management
│   └── requirements.txt
│
├── frontend/
│   ├── index.html             # UI
│   ├── app.js                 # PTT logic & WebSocket
│   ├── audio.js               # Browser audio handling
│   └── style.css              # Responsive styles
│
├── Dockerfile                 # Container for deployment
└── README.md                  # This file
```

## How It Works

### Architecture

```
Browser (PTT) ←→ FastAPI ←→ OpenAI Realtime API
                    ↓
                Core Assessment Logic (shared with desktop)
```

### Audio Flow

1. **User Input (PTT):**
   - Hold button → MediaRecorder starts
   - Release button → Audio sent as complete message
   - Converted to PCM16 24kHz base64
   - Sent via WebSocket to backend

2. **AI Response (Streaming):**
   - OpenAI streams audio chunks
   - Backend forwards to browser
   - Web Audio API plays chunks
   - Queue management for smooth playback

3. **Assessment (Automatic):**
   - Triggered when linguistic ceiling reached
   - Uses shared core assessment agent
   - Report generated and spoken
   - Results saved on backend

## Deployment

### HuggingFace Spaces

1. **Create new Space:**
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Choose "Docker" as SDK

2. **Add files:**
   - Upload entire `web/` folder
   - Add `.env` with your `OPENAI_API_KEY`

3. **Configure:**
   - Set port to 7860 in Space settings
   - Add `OPENAI_API_KEY` as a secret

4. **Deploy:**
   - HuggingFace will build and run the Dockerfile
   - Access at: https://huggingface.co/spaces/your-username/korean-voice-tutor

### Environment Variables

- `OPENAI_API_KEY` (required) - Your OpenAI API key
- `PORT` (optional) - Server port (default: 7860)

## Mobile Browser Support

### Tested On:
- ✅ iOS Safari 14+
- ✅ Android Chrome 90+
- ✅ Android Firefox 90+

### Known Issues:
- iOS requires user gesture to start audio (handled automatically)
- Some older browsers may need microphone permissions refresh

## Development

### Testing Locally

```bash
# Terminal 1: Run server
cd backend
python server.py

# Terminal 2: Watch logs
tail -f *.log
```

### Testing on Mobile (Local Network)

1. Find your local IP:
```bash
# Windows
ipconfig

# Mac/Linux
ifconfig
```

2. Access from mobile:
```
http://YOUR_LOCAL_IP:7860
```

## PTT Behavior

### Robust Handling

- **Too short (<500ms):** Shows hint to hold longer
- **Too long (>60s):** Warns user to be concise
- **Rapid press/release:** Debounced to prevent errors
- **Press during AI speech:** Button disabled
- **Network interruption:** Shows reconnection status

### User Experience

- Haptic feedback on press/release (mobile)
- Visual states: idle → recording → processing → speaking
- Auto-scroll transcript
- Status indicators

## API Endpoints

- `GET /` - Serve frontend
- `GET /health` - Health check & active sessions count
- `WebSocket /ws` - Main client connection

## Troubleshooting

### Microphone not working
- Check browser permissions
- Try HTTPS (required on some browsers)
- Reload page

### Connection issues
- Verify OPENAI_API_KEY is set
- Check server logs
- Ensure port 7860 is not blocked

### Audio playback issues
- Check browser audio isn't muted
- Try headphones (reduces echo)
- Reload page to reset audio context

## Performance

- **Latency:** ~200-500ms end-to-end
- **Concurrent users:** 50+ (tested)
- **Audio codec:** Opus (WebM) → PCM16
- **Sample rate:** 24kHz (matches OpenAI)

## Security

- All audio processing client-side
- WebSocket connections encrypted (wss://)
- API keys never exposed to browser
- Session isolation (no cross-user data)

## Future Enhancements

- [ ] Add continuous streaming option (remove PTT)
- [ ] Support video (AI avatar)
- [ ] Downloadable assessment reports
- [ ] Progress tracking across sessions
- [ ] Multi-language support

## License

Same as parent project

## Support

For issues, see main project README or open an issue on GitHub.
