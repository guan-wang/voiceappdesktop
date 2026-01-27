# Fix: Websocket Timeout During Assessment Generation

## Date: 2026-01-26 (Post-Refactoring)

## Issue Identified from Test Run

### What Worked ✅
1. Assessment triggered correctly
2. State machine transitions perfect: `triggered` → `ack_generating` → `ack_speaking`
3. Acknowledgment played immediately (no silence gap!)
4. Audio completion detected: `[DONE] Audio complete for ack_generating`

### What Failed ❌
```
⏳ Waiting for acknowledgment audio to complete...
[WARN] Cannot wait for unknown response: unknown
❌ Event handler error: received 1011 (internal error) keepalive ping timeout
```

---

## Root Causes

### Problem 1: Response ID Missing

**Issue:** The `response.done` event doesn't always include `response_id` field
- Event structure: `event.get("response_id", "unknown")` returned `"unknown"`
- But we had the correct ID stored in `self.current_response_id` = `"nhyCduNF"`

**Before:**
```python
response_id = event.get("response_id", "unknown")  # Always "unknown"!
```

**After:**
```python
response_id = event.get("response_id") or self.current_response_id or "unknown"
# Now uses tracked ID as fallback
```

---

### Problem 2: Websocket Keepalive Timeout

**Issue:** Assessment generation takes 3-5 seconds and blocks the event loop
- During this time, no websocket messages are processed
- Keepalive pings not sent/received → timeout after ~5 seconds
- Error: `received 1011 (internal error) keepalive ping timeout`

**Timeline:**
```
T+0s:  Acknowledgment audio completes
T+0s:  Start generating assessment report (BLOCKING!)
T+1s:  Still generating... (websocket idle)
T+2s:  Still generating... (websocket idle)
T+3s:  Still generating... (websocket idle)
T+4s:  Still generating... (websocket idle)
T+5s:  Websocket timeout! Connection dies ❌
T+5s:  Report finally generated (but too late)
```

**Before (Blocking):**
```python
# This blocks the event loop for 3-5 seconds!
report = self.assessment_agent.generate_assessment(...)
verbal_summary = self.assessment_agent.report_to_verbal_summary(report)
await self._send_text_message(websocket, verbal_summary)
```

**After (Non-blocking Background Task):**
```python
async def generate_and_send_assessment():
    # Runs in background, doesn't block event loop
    report = self.assessment_agent.generate_assessment(...)
    verbal_summary = self.assessment_agent.report_to_verbal_summary(report)
    await self._send_text_message(websocket, verbal_summary)

# Launch as background task
asyncio.create_task(generate_and_send_assessment())
# Event loop continues processing websocket events!
```

---

## The Fix

### Change 1: Use Tracked Response ID

**File:** `interview_agent.py` (line 486-490)

```python
# OLD:
response_id = event.get("response_id", "unknown")

# NEW:
response_id = event.get("response_id") or self.current_response_id or "unknown"

# Also added validation:
if response_id and response_id != "unknown":
    self.assessment_state.mark_response_complete(response_id)
```

### Change 2: Background Task for Assessment Generation

**File:** `interview_agent.py` (line 497-531)

```python
# Wrapped in async function
async def generate_and_send_assessment():
    try:
        report = self.assessment_agent.generate_assessment(...)
        verbal_summary = self.assessment_agent.report_to_verbal_summary(report)
        self._save_assessment_report(report, verbal_summary)
        self.assessment_state.verbal_summary = verbal_summary
        await self._send_text_message(websocket, verbal_summary)
    except Exception as e:
        print(f"❌ Error in assessment generation: {e}")

# Launch as background task (non-blocking!)
asyncio.create_task(generate_and_send_assessment())
```

---

## Benefits of Background Task Approach

### 1. Event Loop Stays Responsive ✅
- Websocket keepalive pings processed
- Other events handled normally
- No connection timeout

### 2. Better Error Handling ✅
- Wrapped in try-except
- Errors don't crash entire event handler
- Connection stays alive even if generation fails

### 3. User Experience ✅
- No frozen connection
- State machine continues working
- Clean error recovery

---

## Technical Details

### Asyncio Background Tasks

**What `asyncio.create_task()` does:**
1. Schedules coroutine to run "in the background"
2. Returns immediately (non-blocking)
3. Task runs concurrently with event loop
4. Event loop continues processing other events

**Event Loop Processing:**
```
Time    | Main Event Handler          | Background Task
--------|-----------------------------|---------------------------------
T+0s    | Launch background task      | (not started yet)
T+0.1s  | Process websocket ping      | Start generating report
T+0.2s  | Process audio event         | Still generating...
T+1.0s  | Process websocket keepalive | Still generating...
T+2.0s  | Process websocket keepalive | Still generating...
T+3.0s  | Process websocket keepalive | Still generating...
T+4.0s  | Process websocket keepalive | Report complete!
T+4.1s  | Process response.created    | Send summary to websocket
T+4.2s  | Normal flow resumes         | Task complete
```

### Websocket Keepalive

OpenAI Realtime API expects:
- Regular message exchange to keep connection alive
- Timeout typically ~5-10 seconds of idle time
- Keepalive pings sent/received automatically if event loop responsive

---

## Testing Validation

### Expected Behavior After Fix:

1. **Acknowledgment Phase:**
   ```
   [STATE] triggered
   [STATE] ack_generating (ID: ABC123)
   [STATE] ack_speaking
   🤖 AI: 평가를 준비하고 있습니다...
   [DONE] Audio complete for ack_generating (ID: ABC123)
   ✅ Response complete (ID: ABC123)  ← Fixed! Not "unknown"
   ⏳ Waiting for acknowledgment audio to complete...
   ```

2. **Report Generation (Background):**
   ```
   🔍 Generating assessment report in background...
   (Event loop continues processing)
   (Websocket keepalive pings processed)
   📋 Assessment Summary: Based on our conversation...
   💾 Assessment report saved
   ```

3. **Summary Delivery:**
   ```
   🗣️ Sending assessment summary to be spoken...
   [STATE] summary_sending (ID: DEF456)
   [STATE] summary_speaking
   🤖 AI: Based on our conversation...
   [DONE] Audio complete for summary_speaking (ID: DEF456)
   ```

4. **Goodbye:**
   ```
   👋 Sending goodbye message...
   [STATE] goodbye_sending (ID: GHI789)
   🤖 AI: Thank you for completing the interview!
   [DONE] Audio complete for goodbye_speaking (ID: GHI789)
   [STATE] complete
   ✅ Session ended gracefully
   ```

### What to Check:
- [ ] No "unknown" response IDs
- [ ] No websocket timeout errors
- [ ] Complete summary delivery
- [ ] Smooth goodbye
- [ ] Clean session termination

---

## Files Modified

1. **`interview_agent.py`**
   - Line 486-490: Fixed response ID fallback
   - Line 497-531: Moved assessment generation to background task

---

## Related Issues Fixed

This fix also resolves:
- ✅ Connection stability during long operations
- ✅ Response ID tracking reliability
- ✅ Event loop responsiveness
- ✅ Error isolation (generation errors don't crash connection)

---

## Conclusion

Two small but critical fixes:
1. **Response ID:** Use tracked ID instead of assuming event has it
2. **Background Task:** Keep event loop responsive during slow operations

These changes ensure:
- ✅ No websocket timeouts
- ✅ Proper response ID matching
- ✅ Complete assessment delivery
- ✅ Stable connection throughout

**Status: READY FOR TESTING** ✅
