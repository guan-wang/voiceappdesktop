# Quick Start Guide

Get up and running in 5 minutes!

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note:** This installs OpenAI Python SDK 1.102.0+ with support for the latest Realtime API (January 2026)

### 2. Set API Key
Create a `.env` file:
```
OPENAI_API_KEY=sk-your-key-here
```

### 3. Test Setup
```bash
python test_setup.py
```

### 4. Run the App
```bash
python app.py
```

## 🎯 What to Expect

1. The app will connect to OpenAI's Realtime API
2. Audio streams will initialize
3. You'll see: "✅ Ready! Start speaking in Korean..."
4. **Start speaking** - the AI will respond in simple Korean
5. Press `Ctrl+C` to stop

## 💡 Tips

- **Speak clearly** into your microphone
- **Wait for responses** - the AI needs a moment to process
- **Start simple** - try greetings like "안녕하세요" (hello)
- **Be patient** - first connection may take a few seconds

## 🐛 Common Issues

**No audio?**
- Check microphone permissions
- Verify audio devices in system settings

**Connection failed?**
- Check your internet connection
- Verify API key is correct
- Ensure you have API credits

**Import errors?**
- If using `uv`: `uv pip install -r requirements.txt`
- If using `pip`: `pip install -r requirements.txt`
- On Windows with `pip`: If PyAudio fails, try `pip install pipwin && pipwin install pyaudio`

## 📚 Next Steps

- Read `README.md` for detailed documentation
- Check `SETUP_GUIDE.md` for troubleshooting
- Customize the tutor in `app.py` → `get_system_instructions()`

## 🎓 Learning Korean

The tutor is configured to:
- Use **simple Korean** words and phrases
- Speak **slowly and clearly**
- Focus on **everyday conversations**
- Be **encouraging and patient**

Try these phrases to get started:
- 안녕하세요 (Hello)
- 감사합니다 (Thank you)
- 이름이 뭐예요? (What's your name?)
- 오늘 날씨가 좋아요 (The weather is nice today)
