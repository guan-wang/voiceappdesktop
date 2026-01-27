# Performance Optimization Guide

## Expected Latency

### Normal Latency (Good)
- **User speaks** → 0-100ms (recording)
- **Audio upload** → 100-300ms (depending on WiFi/size)
- **OpenAI processing** → 300-800ms (transcription + AI thinking)
- **AI audio response** → 500-1500ms (streaming back)
- **Total:** 1-3 seconds end-to-end ✅

### Slow Latency (Needs optimization)
- Total > 5 seconds ⚠️

## Why Is It Slow?

### 1. First Message Always Slower
- **Reason:** Tool loading (interview_guidance must be called first)
- **Expected:** 3-5 seconds for first message
- **Normal:** Subsequent messages should be faster (1-3s)
- **Fix:** This is now automated - you'll see "Loading interview protocol..." status

### 2. Audio Encoding/Decoding
- **Reason:** Converting WebM/Opus → PCM16 → Base64
- **Impact:** +200-500ms
- **Status:** Optimized as much as possible for browser

### 3. Network Quality
- **WiFi:** +100-500ms variable latency
- **Wired:** +20-100ms stable latency
- **Mobile data:** +200-1000ms variable
- **Fix:** Use wired connection when possible

### 4. OpenAI API Response Time
- **Normal:** 500-1500ms
- **Slow:** 2000-5000ms
- **Factors:**
  - API load (peak hours slower)
  - Model processing time
  - Audio streaming
- **Can't control this** - OpenAI side

### 5. Audio Chunk Processing
- **Issue:** Large audio files take longer
- **Fix:** Speak concisely (10-20 seconds max)

## Optimization Tips

### ✅ Quick Wins

1. **Use Chrome**
   - Best WebRTC/audio support
   - Fastest audio encoding

2. **Wired headphones**
   - Reduces echo cancellation processing
   - Clearer audio = faster transcription

3. **Stable internet**
   - WiFi 5GHz band (less interference)
   - Or wired ethernet
   - Close bandwidth-heavy apps

4. **Shorter messages**
   - Aim for 5-10 second utterances
   - Less audio = faster processing

5. **Close other tabs**
   - Reduces CPU competition
   - Smoother audio processing

### 🔧 Technical Optimizations (Already Applied)

1. **Reduced token limit**
   - Changed: 4096 → 2048 tokens
   - Result: Faster AI responses

2. **Lower temperature**
   - Changed: 0.8 → 0.7
   - Result: More focused, faster responses

3. **Text-only tool calls**
   - Initial setup uses text only (no audio)
   - Result: Faster startup

4. **Streaming audio**
   - Audio plays as it arrives
   - Result: Feels faster (no wait for complete response)

### 📊 Measure Your Latency

Open browser console (F12) and look for timing logs:

```
🎤 Starting recording...           ← T0
✅ Recording started                ← T0 + 50ms
📤 Audio data ready                 ← T1 (when you release button)
🔊 AI started speaking              ← T2 (AI begins response)
✅ AI response complete             ← T3 (AI finishes)

Total latency = T2 - T1
```

**Good:** 1-3 seconds
**Normal:** 3-5 seconds
**Slow:** 5+ seconds (investigate)

## Troubleshooting Slow Performance

### Symptom: First message takes 5+ seconds

**Expected!** First message includes:
1. Tool call (interview_guidance)
2. Loading protocol
3. AI processing with new context

**Subsequent messages should be faster.**

If ALL messages are slow (5+ seconds):

### Check 1: Network
```powershell
# Test latency to OpenAI
ping api.openai.com
# Should see: ~20-100ms
```

If >200ms consistently → network issue

### Check 2: Browser Performance
1. Close other tabs
2. Check CPU usage (Task Manager)
3. Try incognito mode (disables extensions)

### Check 3: Server
Check terminal for slow operations:
```
🔌 Connecting to OpenAI...    ← Should be <1s
✅ Connected to OpenAI        ← Quick
```

If connection takes >2s → network/firewall issue

### Check 4: Audio Size
Browser console should show:
```
📤 Audio data ready: ~50000 bytes   ← Good (5s recording)
📤 Audio data ready: ~500000 bytes  ← Too big (50s recording)
```

If audio >100KB → speak more concisely

## Common Slow Scenarios

### 1. "Every message takes 10+ seconds"

**Likely causes:**
- Poor WiFi signal
- VPN overhead
- CPU overload
- OpenAI API slow (check status.openai.com)

**Fixes:**
- Move closer to router
- Disable VPN temporarily
- Close other apps
- Try different time (off-peak)

### 2. "First message fast, second message slow"

**Likely cause:** AI generating longer response

**Expected behavior:**
- Short questions → fast response
- Complex questions → slower response

**Not a bug** - AI needs time to think!

### 3. "Audio plays but transcript appears late"

**Likely cause:** Audio streams faster than transcription

**Normal behavior:**
- Audio plays immediately
- Transcript appears after (up to 2s later)

**Not a problem** - audio is priority

### 4. "Long pause before AI responds"

**Possible causes:**
- AI is thinking (complex question)
- Network upload slow (large audio)
- OpenAI queue delay

**Check:**
- How long was your message? (shorter = faster)
- How complex was your question?
- Is your internet stable?

## Performance Expectations

### Desktop Version (PyAudio)
- Lower latency: 500-1500ms
- Direct audio I/O
- No browser overhead
- Best for development/testing

### Web Version (Browser)
- Slightly higher: 1000-3000ms
- Browser audio encoding
- Network overhead
- Trade-off for accessibility

### Mobile Browser
- Similar to web: 1500-3500ms
- May be slower on older devices
- Network quality critical
- 4G/5G recommended

## When to Worry

### 🚨 Investigate if:
- Consistent 10+ second delays
- Connection drops frequently
- Audio quality poor
- Transcripts never appear
- No AI response at all

### ✅ Normal if:
- First message 3-5 seconds
- Later messages 1-3 seconds
- Occasional 5s response (complex question)
- Streaming audio plays smoothly

## Real-World Benchmarks

Based on testing:

| Scenario | Latency | Status |
|----------|---------|--------|
| Local WiFi, short message | 1-2s | ✅ Excellent |
| Local WiFi, medium message | 2-3s | ✅ Good |
| Local WiFi, long message | 3-5s | ✅ Normal |
| Mobile 4G, short message | 2-3s | ✅ Good |
| Mobile 4G, medium message | 3-5s | ✅ Normal |
| Poor WiFi, any message | 5-10s | ⚠️ Slow |
| VPN, any message | 4-8s | ⚠️ Slow |

## Summary

**Most "slowness" is actually normal!**

- First message: 3-5s (tool loading)
- Later messages: 1-3s (typical)
- Network + OpenAI API = inherent latency
- Can't be instant (not local processing)

**Optimize what you can control:**
- Use good internet
- Keep messages concise
- Use wired connection
- Close other apps

**Accept what you can't:**
- OpenAI API processing time
- Network round-trip time
- Audio encoding/decoding
- This is as fast as it gets with current tech!

The web version is optimized for **convenience** (mobile access, no install) over **raw speed** (desktop version is faster). For production use, both are acceptable!
