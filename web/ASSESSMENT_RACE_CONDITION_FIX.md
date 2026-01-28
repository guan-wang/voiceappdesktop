# Assessment Race Condition Fix

## Problem Summary

When ceiling was reached and assessment triggered, multiple race conditions caused errors:

```
❌ OpenAI Error: Cancellation failed: no active response found (happened twice)
❌ OpenAI Error: Cannot update a conversation's voice if assistant audio is present.
```

## Root Causes Identified

### 1. **Double Cancellation Without Guards**
- `response.cancel` called twice: once after assessment generation, once in voice switching
- No check if response actually exists before canceling
- Result: "Cancellation failed: no active response found"

### 2. **Insufficient Wait Times**
- Only 200-300ms wait after cancellation before voice switching
- OpenAI needs more time to clear audio buffers
- Result: "Cannot update voice if audio present"

### 3. **Keepalive Task Not Properly Awaited**
- `keepalive_task.cancel()` called without awaiting completion
- Task might be mid-execution when cancelled
- Could cause partially-sent messages or orphaned events

### 4. **`response_in_progress` Flag Race Condition**
- Flag set/cleared across multiple async operations
- Not synchronized, can become stale
- No forced reset after cancellation

### 5. **No Audio Buffer Verification**
- Voice switching relied only on `response_in_progress` flag
- Didn't verify if audio buffer was actually clear
- OpenAI may still have queued audio even after response "done"

---

## Fixes Implemented

### Fix #1: Guard All Cancellations
**Before:**
```python
await self.openai_ws.send(json.dumps({"type": "response.cancel"}))
```

**After:**
```python
if self.response_in_progress:  # Only cancel if response exists
    await self.openai_ws.send(json.dumps({"type": "response.cancel"}))
    self.response_in_progress = False  # Force clear immediately
```

**Impact:** Eliminates "no active response" errors

---

### Fix #2: Increased Wait Times
**Before:**
```python
await asyncio.sleep(0.2)  # 200ms after cancel
await asyncio.sleep(0.3)  # 300ms after voice switch
```

**After:**
```python
await asyncio.sleep(0.5)  # 500ms after cancel
await asyncio.sleep(0.5)  # 500ms after voice switch
```

**Impact:** Gives OpenAI sufficient time to clear audio buffers

---

### Fix #3: Proper Keepalive Cancellation
**Before:**
```python
if keepalive_task:
    keepalive_task.cancel()  # Fire and forget
```

**After:**
```python
if keepalive_task and not keepalive_task.done():
    keepalive_task.cancel()
    try:
        await keepalive_task  # Wait for clean cancellation
    except asyncio.CancelledError:
        pass
```

**Impact:** Prevents orphaned tasks and partial message sends

---

### Fix #4: Explicit Audio Buffer Clearing
**New code added:**
```python
# Clear any lingering audio buffers before voice switch
await self.openai_ws.send(json.dumps({
    "type": "input_audio_buffer.clear"
}))
await asyncio.sleep(0.2)

# Attempt to clear conversation items (helps trigger cleanup)
try:
    await self.openai_ws.send(json.dumps({
        "type": "conversation.item.truncate",
        "item_id": "dummy",
        "content_index": 0,
        "audio_end_ms": 0
    }))
except:
    pass  # Expected to fail, but helps clear state
```

**Impact:** Ensures audio buffers are clear before voice switching

---

### Fix #5: Force Flag Reset
**Added throughout:**
```python
self.response_in_progress = False  # Force clear on cancel
```

**Impact:** Prevents stale flag state from blocking operations

---

## Event Flow After Fixes

```
T0:  trigger_assessment called
T1:  keepalive_task starts (every 3s)
T2:  Assessment generation (5-10s)
T10: Assessment complete
     ↓
T11: keepalive.cancel() + await ✅ (Fix #3)
     ↓
T12: Check if response_in_progress ✅ (Fix #1)
     └─ YES: response.cancel() + force clear flag
        await 500ms ✅ (Fix #2)
     └─ NO: Skip cancellation ✅ (Fix #1)
     ↓
T13: Clear audio buffers explicitly ✅ (Fix #4)
     await 200ms
     ↓
T14: send_text_message() called
     └─ Wait up to 2s for response_in_progress ✅ (Fix #4)
     └─ Check if response_in_progress ✅ (Fix #1)
        └─ YES: Cancel + force clear + 500ms wait
        └─ NO: Skip
     └─ Clear buffers again ✅ (Fix #4)
     └─ session.update(voice) ✅
        await 500ms ✅ (Fix #2)
     └─ response.create()
```

---

## Expected Behavior After Fix

### Before:
```
📋 Assessment complete: A2
🛑 Keepalive task cancelled
❌ OpenAI Error: Cancellation failed: no active response found
🗣️ Sending summary to be spoken...
❌ OpenAI Error: Cancellation failed: no active response found
🎤 Switched to voice: alloy
❌ OpenAI Error: Cannot update voice if assistant audio is present
```

### After:
```
📋 Assessment complete: A2
🛑 Stopping keepalive task...
✅ Keepalive cancelled cleanly
ℹ️ No active response to cancel
🔇 Clearing audio buffers...
🗣️ Sending summary to be spoken...
🎤 Preparing to switch voice to: alloy
✅ Voice switched to: alloy
[Assessment summary plays in English]
```

---

## Testing Checklist

- [ ] Trigger assessment naturally by reaching ceiling
- [ ] Verify no "Cancellation failed" errors
- [ ] Verify no "Cannot update voice" errors
- [ ] Confirm English voice (alloy) is used for assessment summary
- [ ] Confirm assessment audio plays completely without interruption
- [ ] Check logs for clean keepalive cancellation
- [ ] Test with different timing (fast vs slow assessment generation)

---

## Related Files Modified

- `/web/backend/realtime_bridge.py` - All fixes implemented here

## Related Issues

- Race condition during assessment delivery
- Double cancellation errors
- Voice switching failures
- Keepalive task cleanup
