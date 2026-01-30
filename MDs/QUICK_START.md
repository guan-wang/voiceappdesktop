# Quick Start Guide - Korean Voice Tutor

## 🎯 What You Have Now

You have a **fully functional** Korean language proficiency assessment system with:

1. **Desktop Version** - Continuous streaming voice interview
2. **Web Version** - Mobile-optimized PTT interface
3. **Shared Core** - Same assessment logic for both

## 📁 New Structure

```
korean_voice_tutor/
├── core/          # Shared assessment logic ✅
├── desktop/       # Desktop app (refactored) ✅
└── web/           # Web app (NEW) ✅
    ├── backend/   # FastAPI server
    └── frontend/  # Browser UI
```

## 🚀 Quick Start

### Install Dependencies (Choose One Method)

**Method 1: Using UV (Recommended - Fast! ⚡)**
```bash
# Install everything
uv sync

# Or install only what you need
cd desktop && uv sync  # For desktop only
cd web/backend && uv sync  # For web only
```

**Method 2: Using pip (Traditional)**
```bash
cd desktop && pip install -r ../requirements.txt  # For desktop
cd web/backend && pip install -r requirements.txt  # For web
```

See `UV_GUIDE.md` for complete UV documentation.

### Option 1: Run Desktop Version

```bash
cd desktop
uv run python app_v2.py  # With UV
# OR
python app_v2.py  # With regular Python
```

**What happens:**
- Opens microphone/speakers
- Connects to OpenAI
- Starts continuous voice interview
- Same as before, just refactored!

### Option 2: Run Web Version

```bash
cd web/backend
uv run python server.py  # With UV
# OR
python server.py  # With regular Python
```

Then open: **http://localhost:7860**

**What happens:**
- Server starts on port 7860
- Open in browser (works on phone!)
- Hold button to speak
- Release to send

## 📱 Testing on Mobile

### Same WiFi Method

1. **Find your computer's IP:**
```bash
# Windows
ipconfig
# Look for IPv4 Address (e.g., 192.168.1.100)

# Mac/Linux
ifconfig
# Look for inet address
```

2. **Start web server:**
```bash
cd web/backend
python server.py
```

3. **On your phone, open:**
```
http://YOUR_IP_ADDRESS:7860
```

Example: `http://192.168.1.100:7860`

## ⚙️ Configuration

### Set up .env file

**For desktop:**
```bash
# Already configured (use existing .env)
```

**For web:**
```bash
cd web
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-your-key
```

**Note:** You can use UV or pip for package management. See `UV_GUIDE.md` for UV-specific commands.

## 🧪 Testing Checklist

### Desktop Version
- [ ] Audio initializes
- [ ] Can speak Korean
- [ ] AI responds in Korean
- [ ] Assessment triggers
- [ ] Report generated
- [ ] Session ends gracefully

### Web Version
- [ ] Server starts
- [ ] Page loads in browser
- [ ] Microphone permission granted
- [ ] PTT button works (hold/release)
- [ ] Audio plays back
- [ ] Transcript appears
- [ ] Works on mobile

## 🐛 Troubleshooting

### Desktop Issues

**Problem:** Import errors
```bash
# Solution: Update Python path
cd desktop
python app_v2.py
```

**Problem:** Audio not working
```bash
# Solution: Check PyAudio installed
pip install pyaudio
```

### Web Issues

**Problem:** Server won't start
```bash
# Solution: Install dependencies
cd web/backend
pip install -r requirements.txt
```

**Problem:** Can't access on phone
```bash
# Solution: Check firewall
# Windows: Allow Python through firewall
# Mac: System Preferences → Security
```

**Problem:** Microphone not working
```
# Solution: Grant browser permissions
# Settings → Privacy → Microphone → Allow
```

## 📊 Comparing Both Versions

### When to Use Desktop

✅ Development/testing
✅ Local interviews
✅ Low latency needed
✅ Continuous conversation preferred

### When to Use Web

✅ Multiple users
✅ Mobile access
✅ Cloud deployment
✅ Remote interviews
✅ PTT interface

## 🌐 Deploying to HuggingFace

### Step 1: Prepare

```bash
cd web
# Make sure .env.example exists
# Make sure Dockerfile exists
```

### Step 2: Create Space

1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Choose "Docker" SDK
4. Name it "korean-voice-tutor"

### Step 3: Upload Files

Upload entire `web/` folder:
- `backend/`
- `frontend/`
- `Dockerfile`
- `README.md`
- `.env.example`

### Step 4: Configure

1. Add Secret: `OPENAI_API_KEY` = your key
2. Space will auto-build
3. Access at: `https://huggingface.co/spaces/YOUR_USERNAME/korean-voice-tutor`

## 🔧 Development Workflow

### Working on Assessment Logic

```bash
# Edit core files - affects BOTH versions
code core/assessment_agent.py
```

### Working on Desktop

```bash
# Edit desktop files - affects ONLY desktop
cd desktop
code audio/audio_manager.py
python app_v2.py  # Test
```

### Working on Web

```bash
# Edit web files - affects ONLY web
cd web
code frontend/app.js
cd backend && python server.py  # Test
```

## 📈 What's Different?

### Desktop (Refactored)

**Before:** 895-line monolithic file
**After:** Modular 9-file structure
**Function:** Identical

**Benefits:**
- Easier to maintain
- Easier to test
- Easier to extend
- Ready for web version

### Web (New)

**Architecture:** Browser → FastAPI → OpenAI
**Interface:** Push-to-Talk
**Deployment:** HuggingFace Spaces

**Benefits:**
- Mobile-friendly
- Multi-user support
- Cloud-deployable
- No PyAudio needed

## 🎓 Understanding the Code

### Core Files (Shared)

- `core/assessment_agent.py` - Generates CEFR reports
- `core/assessment_state_machine.py` - Manages assessment flow
- `core/tools/` - Interview protocols

**These are used by BOTH desktop and web!**

### Desktop Files

- `desktop/audio/` - PyAudio for mic/speakers
- `desktop/interview_agent_v2.py` - Desktop orchestrator
- `desktop/handlers/` - Event processing

### Web Files

- `web/backend/server.py` - FastAPI server
- `web/backend/realtime_bridge.py` - OpenAI connector
- `web/frontend/app.js` - Browser PTT logic

## 💡 Next Steps

### Immediate (Today)

1. Test desktop version: `cd desktop && python app_v2.py`
2. Test web locally: `cd web/backend && python server.py`
3. Test on mobile (same WiFi)

### Short-term (This Week)

1. Deploy web to HuggingFace
2. Test with real users
3. Gather feedback

### Long-term (Future)

1. Add features based on usage
2. Improve UI/UX
3. Add analytics
4. Consider mobile native app

## 📚 Documentation

- `ARCHITECTURE.md` - Detailed architecture overview
- `REFACTORING_GUIDE.md` - How desktop was refactored
- `web/README.md` - Web-specific documentation
- `desktop/` - Desktop-specific docs

## 🆘 Getting Help

### Check These First

1. **Logs:** Look at console output
2. **Network:** Check firewall/WiFi
3. **Permissions:** Grant microphone access
4. **API Key:** Verify in .env

### Common Issues

**Desktop won't run:**
```bash
cd desktop
python -c "import sys; print(sys.path)"
# Make sure parent dir is in path
```

**Web won't connect:**
```bash
# Check server is running
curl http://localhost:7860/health
```

**Mobile can't access:**
```bash
# Try localhost first
http://localhost:7860
# Then try IP
http://192.168.x.x:7860
```

## ✅ Success Criteria

You're ready to go when:

- [ ] Desktop version runs and completes interview
- [ ] Web version loads in browser
- [ ] PTT button records and sends audio
- [ ] AI responds with voice
- [ ] Transcripts appear correctly
- [ ] Assessment generates at end
- [ ] Mobile browser works (if needed)

## 🎉 You're All Set!

Your Korean Voice Tutor is now:
- ✅ Refactored (maintainable)
- ✅ Modular (extensible)
- ✅ Multi-platform (desktop + web)
- ✅ Mobile-ready (PTT interface)
- ✅ Cloud-ready (HuggingFace)

**Start with:** `cd desktop && python app_v2.py`

Then explore the web version when ready!
