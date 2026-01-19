# Setup Guide - Korean Voice Tutor

## Step-by-Step Setup Instructions

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Note for Windows users:** 
- **If using `uv`:** `uv pip install pyaudio` should work directly
- **If using `pip`:** If you encounter issues installing PyAudio, try:
  ```bash
  pip install pipwin
  pipwin install pyaudio
  ```

**Note for macOS users:** You may need to install PortAudio first:
```bash
brew install portaudio
```

**Note for Linux users:**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

### Step 2: Get Your OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign in or create an account
3. Navigate to API Keys section
4. Create a new API key
5. **Important:** Make sure your API key has access to the Realtime API (it may be in beta/preview)

### Step 3: Configure Environment Variables

Create a `.env` file in the `korean_voice_tutor` directory:

```bash
cd korean_voice_tutor
```

Create `.env` file with:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Security Note:** Never commit your `.env` file to version control!

### Step 4: Test Your Setup

Run a quick test to verify everything is configured:

```bash
python -c "import pyaudio; import openai; import websockets; print('✅ All dependencies installed')"
```

### Step 5: Run the Application

```bash
python app.py
```

## Troubleshooting

### Audio Issues

**Problem:** "No module named '_portaudio'"
- **Solution:** Install PortAudio (see Step 1)

**Problem:** "No default input device found"
- **Solution:** 
  - Check your microphone is connected
  - On Windows: Check microphone permissions in Settings
  - On macOS: Check System Preferences > Security & Privacy > Microphone

**Problem:** "No default output device found"
- **Solution:**
  - Check your speakers/headphones are connected
  - Verify audio output device in system settings

### API Issues

**Problem:** "Invalid API key"
- **Solution:** 
  - Verify your API key is correct in `.env`
  - Check that the key hasn't expired
  - Ensure you have API credits

**Problem:** "Model not found" or "Realtime API not available"
- **Solution:**
  - The Realtime API may be in beta - check if you have access
  - Verify the model name is correct
  - Check OpenAI's status page

**Problem:** "WebSocket connection failed"
- **Solution:**
  - Check your internet connection
  - Verify firewall isn't blocking WebSocket connections
  - Try again - may be temporary API issue

### Python Issues

**Problem:** "ModuleNotFoundError"
- **Solution:** Run `pip install -r requirements.txt` again

**Problem:** Python version too old
- **Solution:** Upgrade to Python 3.8 or higher

## Next Steps

Once everything is working:

1. **Test the connection:** Speak into your microphone and see if the AI responds
2. **Adjust settings:** Modify `get_system_instructions()` in `app.py` to customize the tutor
3. **Change voice:** Edit the `voice` parameter (options: alloy, echo, fable, onyx, nova, shimmer)
4. **Experiment:** Try different conversation topics and see how the tutor responds

## Getting Help

If you encounter issues:

1. Check the error message carefully
2. Review the troubleshooting section above
3. Check OpenAI's Realtime API documentation
4. Verify all dependencies are correctly installed

## Important Notes

- **API Costs:** The Realtime API usage is billed - monitor your usage
- **Network:** Requires stable internet connection
- **Privacy:** Audio is sent to OpenAI's servers for processing
- **Beta Feature:** The Realtime API may have limitations or changes
