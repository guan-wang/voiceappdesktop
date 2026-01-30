# Assessment WebSocket Timeout Fix

## Problem

When the assessment was generated successfully but the WebSocket to OpenAI timed out during the speech phase, the frontend would get stuck on the loading screen indefinitely.

### Failure Scenario (Before Fix)

From the logs:
```
✅ Assessment report generated successfully
📝 Verbal summary created
📋 Assessment complete: A2
🛑 Stopping keepalive task...
⚠️ Could not clear audio buffer: received 1011 (internal error) keepalive ping timeout
🗣️ Sending summary to be spoken...
❌ Assessment generation error: ConnectionClosedError (keepalive ping timeout)
```

**Flow:**
1. ✅ Report generated successfully
2. ✅ Keepalive stopped
3. ⚠️ Audio buffer clear failed (WebSocket timeout)
4. ❌ Trying to send summary to be spoken **FAILED** (WebSocket timeout)
5. ❌ Never reached the code to send `assessment_complete` to frontend
6. 🔴 Frontend stuck on loading screen forever

### Root Cause

The code was structured as:
```python
# Generate report
report = generate_assessment()  # Success

# Try to speak summary
await send_text_message(verbal_summary)  # FAILS HERE

# Send report to client (NEVER REACHED)
await send_to_client({"type": "assessment_complete"})
```

If the WebSocket times out during speech, the frontend never receives the `assessment_complete` message, so the loading overlay stays visible forever.

## Solution

Reorder the operations to prioritize showing the visual report:

### New Flow (After Fix)

```python
# Generate report
report = generate_assessment()  # Success

# Send report to client FIRST
await send_to_client({"type": "assessment_complete"})  # ✅ Always happens

# Save report
save_assessment_report()

# Try to speak in background (non-blocking)
try:
    await send_text_message(verbal_summary)
except Exception as e:
    print("Could not send summary for speech")
    # Visual report is already displayed, no problem!
```

### Key Changes

1. **Send `assessment_complete` BEFORE attempting speech**
   - Ensures visual report shows even if speech fails
   - Matches new requirement where report should appear immediately

2. **Wrap speech attempt in try-except**
   - If speech fails, it's caught and logged
   - Doesn't crash the entire assessment flow
   - User still sees the visual report

3. **Better logging**
   - Clear messages about what succeeded and what failed
   - Helps with debugging WebSocket timeout issues

## Code Changes

### File: `realtime_bridge.py`

**Before:**
```python
# Line 461-471
await self.send_text_message(verbal_summary, language="english")

await self.send_to_client({
    "type": "assessment_complete",
    "report": report.model_dump(),
    "summary": verbal_summary
})
```

**After:**
```python
# CRITICAL: Send report to client FIRST
await self.send_to_client({
    "type": "assessment_complete",
    "report": report.model_dump(),
    "summary": verbal_summary
})
print(f"✅ Assessment report sent to client")

# Save report
self.session.save_assessment_report(report, verbal_summary)

# Try to speak in background (non-blocking)
try:
    print(f"🗣️ Sending summary to be spoken...")
    await self.send_text_message(verbal_summary, language="english")
    print(f"✅ Summary sent for speech")
except Exception as e:
    print(f"⚠️ Could not send summary for speech: {e}")
    print(f"ℹ️ Visual report is still displayed to user")
```

## Benefits

### 1. Frontend Never Gets Stuck
- Even if OpenAI WebSocket times out, the visual report shows
- User can proceed by clicking "Begin Path" button
- No infinite loading screens

### 2. Graceful Degradation
- If speech works: User sees report + hears summary ✅
- If speech fails: User sees report (silent) ✅
- Both cases are acceptable user experiences

### 3. Matches New Requirements
- Visual report should appear immediately after assessment
- AI speech is nice-to-have, not critical
- User can stop audio by clicking CTA

### 4. Better Error Recovery
- WebSocket timeouts don't break the entire flow
- Clear logging of what succeeded and what failed
- Easier to debug in production

## Testing

### Test Case 1: Normal Flow
1. Complete assessment conversation
2. Wait for loading screen
3. Visual report should appear
4. AI should speak summary (if WebSocket healthy)
5. Click "Begin Path" → Survey appears

### Test Case 2: WebSocket Timeout During Speech
1. Complete assessment conversation
2. Wait for loading screen
3. Visual report should appear (even if WebSocket times out)
4. AI may not speak (silent report is OK)
5. Click "Begin Path" → Survey appears

### Test Case 3: Complete WebSocket Failure
1. Complete assessment conversation
2. Wait for loading screen
3. If report generation succeeds: Visual report appears
4. If report generation fails: Error message shown
5. Frontend never stuck on loading screen

## Rollback Plan

If issues arise, revert the order:
1. Put `send_text_message()` back before `send_to_client()`
2. Remove try-except around speech attempt
3. But this brings back the original bug (stuck loading screen)

## Related Files

- `/web/backend/realtime_bridge.py` - Main fix
- `/web/frontend/app.js` - Frontend handles assessment_complete
- `/web/frontend/report.js` - Renders visual report

## Date
January 30, 2026

## Status
✅ Fixed - Deployed
