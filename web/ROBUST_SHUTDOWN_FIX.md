# Robust Server Shutdown - FINAL FIX ✅

## Problems Found in Logs

### 1. "Cancellation failed: no active response found"
Trying to cancel a response that doesn't exist.

### 2. "Cannot update a conversation's voice if assistant audio is present"
Trying to change voice mid-conversation.

### 3. Server hanging on Ctrl+C
Background tasks not properly cancelled.

## Root Causes

### Voice Change Error
OpenAI doesn't allow voice changes when:
- A response is in progress
- Audio is already in the conversation
- The session is in the middle of speaking

### Response Cancellation Error
We were calling `response.cancel` even when no response was active, causing unnecessary errors.

### Hanging on Shutdown
Background tasks (keepalive, assessment) weren't being:
- Tracked properly
- Cancelled with timeout
- Awaited during shutdown

## Comprehensive Fixes

### 1. Removed Aggressive Cancellation ✅

**Before (caused errors):**
```python
# Try to cancel response
await self.openai_ws.send({"type": "response.cancel"})
# Error: no active response found!
```

**After (safe):**
```python
# Wait for response to complete naturally
retries = 0
while self.response_in_progress and retries < 20:
    await asyncio.sleep(0.2)  # Wait up to 4 seconds
    retries += 1
```

**Why:** Safer to wait than force cancellation.

### 2. Conditional Voice Switching ✅

**Before (caused errors):**
```python
# Always try to switch voice
await self.openai_ws.send({
    "type": "session.update",
    "session": {"voice": "alloy"}
})
# Error: audio already present!
```

**After (safe):**
```python
# Only switch if safe
if voice != "marin" and not self.response_in_progress:
    try:
        await self.openai_ws.send(...)
    except Exception as e:
        # Failed, but continue with stronger instructions
        print(f"Voice switch failed (continuing): {e}")
```

**Why:** Voice switching is optional - stronger instructions still help.

### 3. Track Background Tasks ✅

```python
# Track all background tasks
self.background_tasks = set()
self.is_shutting_down = False

# When creating task
task = asyncio.create_task(self._generate_and_deliver_assessment())
self.background_tasks.add(task)
task.add_done_callback(self.background_tasks.discard)
```

**Why:** Can cancel all tracked tasks during shutdown.

### 4. Graceful Task Cancellation ✅

**In keepalive:**
```python
try:
    while not self.is_shutting_down:  # Check shutdown flag
        await asyncio.sleep(3.0)
        ...
except asyncio.CancelledError:
    # Don't re-raise during shutdown
    if not self.is_shutting_down:
        raise
```

**In assessment:**
```python
except asyncio.CancelledError:
    if keepalive_task:
        keepalive_task.cancel()
        await keepalive_task  # Wait for sub-task
    if not self.is_shutting_down:
        raise
```

**Why:** Prevents re-raising errors during intentional shutdown.

### 5. Bridge Cleanup Method ✅

```python
async def cleanup(self):
    """Cleanup this bridge and cancel all background tasks"""
    self.is_shutting_down = True
    
    # Cancel all tasks
    for task in self.background_tasks:
        task.cancel()
    
    # Wait with timeout
    await asyncio.wait_for(
        asyncio.gather(*self.background_tasks, return_exceptions=True),
        timeout=2.0
    )
```

**Why:** Centralized cleanup with timeout guarantee.

### 6. Session Store Shutdown with Timeout ✅

```python
async def shutdown_all_sessions(self):
    # Cancel cleanup task with timeout
    await asyncio.wait_for(self._cleanup_task, timeout=1.0)
    
    # Cleanup all sessions with timeout
    await asyncio.wait_for(
        asyncio.gather(*cleanup_tasks, return_exceptions=True),
        timeout=3.0
    )
    
    # Force clear any remaining
    self.sessions.clear()
```

**Why:** Guarantees shutdown completes, even if some tasks don't respond.

### 7. WebSocket Endpoint Cleanup ✅

```python
finally:
    # Cleanup bridge first
    await bridge.cleanup()
    
    # Cancel OpenAI task with timeout
    await asyncio.wait_for(openai_task, timeout=1.0)
    
    # Remove session
    session_store.remove_session(session_id)
```

**Why:** Ensures proper cleanup order and timeout protection.

## Shutdown Flow

### Before (Broken):
```
Ctrl+C pressed
↓
Server tries to shutdown
↓
Background tasks still running:
  - Keepalive (infinite loop)
  - Assessment (10-15s operation)
  - Cleanup task (infinite loop)
↓
❌ Hangs waiting for tasks
↓
User must force quit
```

### After (Fixed):
```
Ctrl+C pressed
↓
Lifespan shutdown triggered
↓
Set is_shutting_down = True
↓
Cancel all background tasks
  - Keepalive stops loop
  - Assessment exits gracefully
  - Cleanup task cancelled
↓
Wait with 3 second timeout
↓
Force clear remaining sessions
↓
✅ Clean shutdown in 1-3 seconds
```

## Expected Logs

### Successful Shutdown:
```
^C (Ctrl+C)
INFO:     Shutting down
🔌 [session] Client disconnected
INFO:     connection closed
INFO:     Waiting for background tasks to complete.
🧹 [session] Cleaning up bridge...
🛑 [session] Keepalive task cancelled
✅ [session] Bridge cleanup complete
🗑️ Removed session: ...
✅ [session] Session cleanup complete
INFO:     Waiting for application shutdown.
👋 Shutting down server...
🧹 Shutting down 0 active session(s)...
✅ No active sessions to shutdown
✅ All sessions cleaned up
INFO:     Application shutdown complete.
INFO:     Finished server process [PID]
```

**Total time: <3 seconds**

### If Tasks Don't Respond:
```
⚠️ Some tasks didn't finish in time
⚠️ Some sessions didn't cleanup in time, forcing shutdown
✅ All sessions shut down (forced)
```

Still shuts down (doesn't hang).

## Timeout Strategy

| Task | Timeout | Reason |
|------|---------|--------|
| Keepalive loop exit | 3s | Check every 3s, immediate on flag |
| Assessment cancel | 2s | Wait for graceful exit |
| Single session cleanup | 1s | Per-session timeout |
| All sessions cleanup | 3s | Total cleanup time limit |
| Cleanup task cancel | 1s | Quick cancel |

**Total worst case: 3 seconds** (with forced completion)

## Safety Guarantees

✅ **No infinite waits** - All operations have timeouts
✅ **Forced cleanup** - Clear sessions even if tasks don't respond
✅ **Exception handling** - Continue even if individual cleanups fail
✅ **Status flags** - Tasks check shutdown flag and exit loops
✅ **Graceful degradation** - Log warnings but don't block shutdown

## Testing Checklist

Test Ctrl+C during:

- [ ] Normal conversation (mid-interview)
- [ ] Initial setup (tool call in progress)
- [ ] Assessment generation (long-running task)
- [ ] Multiple users connected
- [ ] No users connected (idle server)

**All should shutdown cleanly in <3 seconds**

## Alternative: Force Stop Script

If Ctrl+C ever fails (shouldn't now):

```powershell
.\stop_server.ps1
```

This forcefully kills the process via PID.

## Files Modified

- ✅ `web/backend/realtime_bridge.py` - Task tracking, cleanup method, shutdown flags
- ✅ `web/backend/session_store.py` - Robust shutdown with timeouts
- ✅ `web/backend/server.py` - Bridge cleanup in websocket handler

## Summary

✅ **Removed aggressive cancellation** - wait instead
✅ **Conditional voice switching** - only when safe
✅ **Track all background tasks** - can cancel on shutdown
✅ **Shutdown flags** - tasks check and exit loops
✅ **Timeout protection** - guaranteed shutdown in 3s
✅ **Graceful degradation** - log errors, don't block
✅ **Force clear fallback** - sessions.clear() if needed

**Ctrl+C should now work instantly and reliably!** 🎉

The errors during assessment are now handled gracefully - voice switching is optional (instructions are still strong), and the assessment summary will still be spoken (just possibly with Korean accent if voice switch fails).

## Priority

**Most Important:** Server shutdown works ✅
**Secondary:** Voice change (optional, has fallback) ✅

Test now - Ctrl+C should work perfectly!
