# Web App Troubleshooting Guide

## Common Issues and Fixes

### 1. "Recording failed. Please try again."

This error can have several causes. The improved error messages will now tell you exactly what's wrong:

#### A. "Microphone permission denied"

**Problem:** Browser doesn't have permission to access microphone

**Fix:**
1. Look for microphone icon in browser address bar
2. Click it and allow microphone access
3. Refresh the page
4. Try pressing PTT again

**Chrome:**
- Click 🔒 (padlock) in address bar
- Set Microphone to "Allow"
- Reload page

**Firefox:**
- Click 🔒 in address bar  
- Click "✓" next to Microphone
- Reload page

**Safari:**
- Safari → Settings → Websites → Microphone
- Allow for localhost

#### B. "No microphone found"

**Problem:** No microphone detected

**Fix:**
1. Check if microphone is connected
2. On Windows: Settings → Sound → Input → Make sure microphone is not disabled
3. Try unplugging and replugging (USB mic)
4. Refresh the page

#### C. "Microphone already in use"

**Problem:** Another app is using the microphone

**Fix:**
1. Close other apps that might use microphone:
   - Zoom, Teams, Discord
   - Other browser tabs with audio
   - Desktop voice assistants
2. Refresh the page

#### D. "Browser does not support audio recording"

**Problem:** Using unsupported browser

**Supported browsers:**
- ✅ Chrome 60+
- ✅ Firefox 55+
- ✅ Safari 14+
- ✅ Edge 79+

**Fix:**
- Update your browser
- Or use a supported browser

### 2. Button Disabled (Grayed Out)

**Symptoms:**
- PTT button is grayed out
- Can't click it
- Shows "Connecting..." or error message

**Causes & Fixes:**

#### A. Still connecting
- Wait 3-5 seconds for connection
- Should show "Ready to speak" when ready

#### B. Connection failed
- Check internet connection
- Verify server is running
- Check browser console (F12) for errors

#### C. Audio initialization failed
- See issue #1 above
- Check microphone permissions
- Try refreshing page

### 3. No Audio Playback (Can't Hear AI)

**Problem:** You speak, AI responds (transcript appears), but no sound

**Fixes:**

#### A. Check volume
- Computer volume not muted
- Browser tab not muted (check tab icon)
- Speaker/headphones connected

#### B. Audio output device
- Windows: Right-click speaker icon → Open Sound settings → Output
- Make sure correct device selected

#### C. Browser audio permissions
- Some browsers block autoplay audio
- Click anywhere on page to enable audio
- Check browser settings

### 4. Connection Issues

#### A. "Connection lost"

**Fixes:**
1. Check server is running:
   ```powershell
   cd web\backend
   .\start_server.ps1
   ```

2. Check firewall:
   - Allow Python through Windows Firewall
   - Allow port 7860

3. Check network:
   - Is WiFi connected?
   - Try: http://127.0.0.1:7860 instead of localhost

#### B. Can't connect on mobile

**Fixes:**
1. Make sure phone and computer on same WiFi
2. Find computer's IP:
   ```powershell
   ipconfig
   # Look for IPv4 Address
   ```
3. On phone, open: `http://YOUR_IP:7860`
4. Make sure Windows Firewall allows incoming connections

### 5. Slow Response Time

**Problem:** Long delay between speaking and AI response

**Causes:**
- Network latency
- OpenAI API response time
- Large audio files

**Fixes:**
1. Speak more concisely (shorter messages)
2. Check internet speed
3. Try wired connection instead of WiFi

### 6. Transcript Not Appearing

**Problem:** Audio works but no text transcript

**Possible causes:**
- WebSocket connection issue
- Server-side error
- Transcription API issue

**Fixes:**
1. Check browser console (F12) for errors
2. Check server logs in terminal
3. Verify OpenAI API key is valid

### 7. Assessment Not Triggering

**Problem:** Interview continues but never ends

**This is normal!** Assessment only triggers when:
- AI detects linguistic ceiling (user struggles)
- Natural conversation endpoint reached

**Not a bug** - keep conversing!

## Debugging Steps

### 1. Open Browser Console

**Chrome/Edge:** Press `F12` or `Ctrl+Shift+I`
**Firefox:** Press `F12` or `Ctrl+Shift+K`
**Safari:** `Cmd+Option+I`

Look for errors in red.

### 2. Check What's Logged

Good initialization looks like:
```
🚀 Initializing app...
🎤 Requesting microphone access...
✅ Microphone access granted
✅ Audio context created
✅ Audio initialized successfully
✅ WebSocket connected
✅ App initialized successfully
```

### 3. Common Console Errors

| Error | Meaning | Fix |
|-------|---------|-----|
| `NotAllowedError` | Mic permission denied | Allow in browser settings |
| `NotFoundError` | No microphone | Connect microphone |
| `NotReadableError` | Mic in use | Close other apps |
| `WebSocket closed` | Server disconnected | Restart server |
| `NetworkError` | Connection failed | Check internet |

### 4. Test Microphone Separately

Visit: https://www.onlinemictest.com/
- If mic works there but not in app → browser permission issue
- If mic doesn't work there → hardware/driver issue

### 5. Check Server Logs

In terminal where server is running, look for:
```
✅ Created session: xxxxxxxx...
🔌 [xxxxxxxx] Client connected
🔌 [xxxxxxxx] Connecting to OpenAI Realtime API...
✅ [xxxxxxxx] Connected to OpenAI
```

If you see errors → check OpenAI API key

## Browser-Specific Issues

### Chrome
- Most reliable
- Good error messages
- Recommended browser

### Firefox
- May need explicit permission grant
- Check about:permissions

### Safari
- Must explicitly allow microphone in Settings
- May need page reload after permission grant
- iOS Safari: Requires user gesture (button press) to start audio

### Edge
- Same as Chrome (Chromium-based)
- Generally works well

## Mobile-Specific Issues

### iOS Safari
- **Must use https:// for mic access** (or localhost)
- Screen may need to stay on
- Background mode may pause audio
- Recommended: Add to Home Screen for app-like experience

### Android Chrome
- Generally works well
- May need site permissions in Android settings
- Check battery optimization not killing browser

## Still Having Issues?

### Collect Debug Info

1. **Browser:** Chrome 120.0.0 (or your version)
2. **OS:** Windows 11 (or your OS)
3. **Error message:** (exact text)
4. **Console errors:** (screenshot)
5. **Server logs:** (copy from terminal)

### Quick Reset

1. Stop server: `.\stop_server.ps1`
2. Clear browser cache (Ctrl+Shift+Del)
3. Start server: `.\start_server.ps1`
4. Hard refresh page: `Ctrl+F5`
5. Allow microphone when prompted

### Test with Minimal Setup

1. Use Chrome (latest version)
2. Use http://localhost:7860 (not IP)
3. Use wired headphones/mic
4. Close all other apps
5. Try again

If it works → eliminate variables one by one to find culprit.

## Performance Tips

### For Best Experience

✅ **Use wired headphones** - Prevents echo/feedback
✅ **Close unused tabs** - Reduces CPU load
✅ **Stable internet** - WiFi 5GHz or wired
✅ **Updated browser** - Latest version
✅ **Quiet environment** - Better speech recognition

### Reduce Latency

1. Wired ethernet (vs WiFi)
2. Close CPU-heavy apps
3. Shorter utterances
4. Good microphone quality

## Error Code Reference

| Code | Meaning |
|------|---------|
| `NotAllowedError` | Permission denied |
| `NotFoundError` | Device not found |
| `NotReadableError` | Device in use |
| `AbortError` | Operation aborted |
| `NotSupportedError` | Format not supported |
| `TypeError` | Browser incompatible |
| `SecurityError` | HTTPS required |
| `OverconstrainedError` | Constraints can't be met |

## Getting Help

If none of these fixes work:

1. Check browser console (F12)
2. Check server terminal logs
3. Test microphone at https://www.onlinemictest.com/
4. Try different browser
5. Check if issue persists with desktop version

## Known Limitations

- **iOS Safari:** Requires https:// (except localhost)
- **Firefox:** May need manual permission reset
- **Old browsers:** Update to latest version
- **Virtual audio devices:** May not work properly
- **Screen share audio:** Not supported as mic input

Most issues are browser permissions or microphone access! 🎤
