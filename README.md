# Korean Voice Tutor - Real-time AI Language Learning

A simple proof-of-concept for a real-time voice-based Korean language tutor using OpenAI's Realtime API.

## 🎯 Features

- Real-time voice conversation in Korean
- Beginner-friendly Korean language instruction
- Simple, easy-to-understand Korean phrases
- Patient and encouraging teaching style

## 📋 Prerequisites

1. **Python 3.8+** installed
2. **OpenAI API Key** with access to Realtime API
3. **Microphone and speakers** for audio input/output
4. **PortAudio** (required for PyAudio on some systems)

### Installing PortAudio

**Windows:**
- **If using `uv` (recommended):** `uv pip install pyaudio` - usually works without issues
- **If using `pip`:** PyAudio may require Visual C++ Build Tools to compile from source
  - Try: `pip install pyaudio` first
  - If that fails, use: `pip install pipwin && pipwin install pyaudio`
  - Or download PortAudio from: http://files.portaudio.com/download.html

**macOS:**
```bash
brew install portaudio
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

## 🚀 Setup

1. **Clone/Navigate to the project directory:**
   ```bash
   cd korean_voice_tutor
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key:**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

## 🎮 Usage

Run the application:
```bash
python app.py
```

The tutor will:
- Create a Realtime API session
- Initialize audio streams
- Wait for you to start speaking
- Respond in simple Korean

Press `Ctrl+C` to stop the application.

## 📝 Notes

### Current Implementation Status

This is a **basic PoC structure**. The current implementation includes:
- ✅ Session creation with OpenAI Realtime API
- ✅ Audio stream setup (input/output)
- ✅ System instructions for Korean language teaching
- ⚠️ WebSocket connection (needs full implementation)

### Next Steps for Full Implementation

1. **WebSocket Connection:**
   - Implement the full WebSocket protocol for OpenAI Realtime API
   - Handle real-time audio streaming
   - Process incoming audio events

2. **Audio Processing:**
   - Implement proper audio chunking and buffering
   - Handle audio format conversion if needed
   - Add error handling for audio stream issues

3. **Turn Detection:**
   - Implement voice activity detection (VAD)
   - Handle interruptions gracefully
   - Manage conversation flow

4. **Enhanced Features:**
   - Add conversation history
   - Implement difficulty levels
   - Add progress tracking
   - Include pronunciation feedback

## 🔧 Configuration

You can customize the tutor's behavior by modifying the `get_system_instructions()` method in `app.py`:

- Change the teaching style
- Adjust difficulty level
- Modify conversation topics
- Add specific learning goals

## 📚 Resources

- [OpenAI Realtime API Documentation](https://platform.openai.com/docs/guides/realtime)
- [OpenAI Realtime API Reference](https://platform.openai.com/docs/api-reference/realtime)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [OpenAI Realtime Console](https://github.com/openai/openai-realtime-console) - For testing and debugging

## 🔄 Latest Updates (January 2026)

- **Model**: Using `gpt-realtime` (latest stable model)
- **SDK Version**: OpenAI Python SDK 1.102.0+
- **Voice Options**: Latest voices include `marin`, `cedar`, plus classic options: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

## ⚠️ Important Notes

1. **API Access:** Make sure your OpenAI API key has access to the Realtime API (it may be in beta/preview)
2. **Audio Quality:** Ensure good microphone and speaker setup for best experience
3. **Network:** Stable internet connection required for real-time streaming
4. **Costs:** Realtime API usage is billed - monitor your usage

## 🐛 Troubleshooting

**Audio Issues:**
- Check microphone permissions
- Verify audio device selection
- Try different audio formats if needed

**API Connection Issues:**
- Verify your API key is correct
- Check if Realtime API is available in your region
- Ensure you have sufficient API credits

**Import Errors:**
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- On Windows, you may need to install PyAudio wheels separately

## 📄 License

This is a proof-of-concept project for educational purposes.
