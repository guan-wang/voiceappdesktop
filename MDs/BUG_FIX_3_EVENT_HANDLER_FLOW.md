# Bug Fix #3 - Event Handler Flow During Assessment

## The Problem

Even though assessment messages were being sent via `response.create`, the user never heard the audio because **the event handler loop was exiting immediately** after sending the messages.

## Root Cause: Event Handler Loop Exits Too Early

### Original (Broken) Flow:

```
1. trigger_assessment function called
2. Generate assessment report (blocking, ~2-3 seconds)
3. Send response.create for summary ✅
4. await asyncio.sleep(15) ⏰ (just waits, doesn't process events)
5. Send response.create for goodbye ✅
6. await asyncio.sleep(5) ⏰ (just waits, doesn't process events)
7. break ❌ EXIT EVENT HANDLER LOOP
8. Audio responses never processed! ❌
```

### The Critical Issue:

The **event handler loop** is responsible for:
- Receiving WebSocket events
- Processing `response.audio.delta` events (the actual audio data)
- Playing audio via the audio output callback

When you call `break`, the loop exits, so:
- ❌ No more events are processed
- ❌ Audio data never arrives
- ❌ Nothing gets played

### Why `asyncio.sleep()` Doesn't Help:

```python
await self._send_text_message(websocket, text)
await asyncio.sleep(15)  # ❌ This ONLY waits time, doesn't process events!
break  # ❌ Exits the event handler loop immediately
```

`asyncio.sleep()` just pauses execution. It doesn't process the WebSocket event loop. The events are only processed by the `async for message in websocket:` loop in the event handler.

## The Fix: Continue Processing Events Until Responses Complete

### New Flow:

```
1. trigger_assessment function called
2. Generate assessment report (blocking, ~2-3 seconds)
3. Send response.create for summary
4. Increment assessment_responses_pending (now = 1)
5. Send response.create for goodbye
6. Increment assessment_responses_pending (now = 2)
7. CONTINUE running event handler loop ✅
8. Process response.audio.delta events → audio plays 🔊
9. Process response.done event → increment assessment_responses_completed
10. Check if all responses done (completed == pending)
11. If yes, end session gracefully
```

### Key Changes:

#### 1. Track Pending Responses (Lines 43-44)

```python
self.assessment_responses_pending = 0      # How many responses we're waiting for
self.assessment_responses_completed = 0    # How many have finished
```

#### 2. Don't Break Immediately (Lines 495-507)

**Before:**
```python
await self._send_text_message(websocket, verbal_summary)
await asyncio.sleep(15)
await self._send_text_message(websocket, goodbye_msg)
await asyncio.sleep(5)
break  # ❌ Exits immediately
```

**After:**
```python
await self._send_text_message(websocket, verbal_summary)
self.assessment_responses_pending += 1

await self._send_text_message(websocket, goodbye_msg)
self.assessment_responses_pending += 1

print(f"⏳ Waiting for {self.assessment_responses_pending} assessment responses to complete...")
print("💡 The event handler will continue processing until all audio is played.")

# Don't break here! Let the event handler continue
```

#### 3. Track Response Completion (Lines 377-389)

```python
elif event_type == "response.done":
    print("✅ Response complete")
    
    # Check if this is an assessment response
    if self.assessment_triggered and self.assessment_responses_pending > 0:
        self.assessment_responses_completed += 1
        print(f"📊 Assessment response {self.assessment_responses_completed}/{self.assessment_responses_pending} completed")
        
        # If all assessment responses are done, end the session
        if self.assessment_responses_completed >= self.assessment_responses_pending:
            print("\n✅ All assessment responses completed. Ending session...")
            self.should_end_session = True
            self.is_running = False
            await asyncio.sleep(2)  # Brief pause before ending
            break
```

## Detailed Flow Diagram

### WebSocket Connection State:

```
Interview Phase:
├─ WebSocket OPEN ✅
├─ Event handler running ✅
├─ Audio flowing bidirectionally 🔊
└─ User and AI conversing

Ceiling Detected:
├─ trigger_assessment called
├─ WebSocket STILL OPEN ✅
├─ Event handler STILL RUNNING ✅
└─ Assessment generation begins

Assessment Generation:
├─ WebSocket STILL OPEN ✅ (but no new requests)
├─ Event handler STILL RUNNING ✅ (waiting for events)
├─ Assessment agent analyzes transcript
└─ Report generated

Assessment Delivery:
├─ WebSocket STILL OPEN ✅
├─ Event handler STILL RUNNING ✅
├─ Send response.create #1 (summary)
├─ Send response.create #2 (goodbye)
├─ Event handler processes response.audio.delta events
├─ Audio plays to user 🔊
├─ response.done events increment counter
└─ When counter == pending, break and close

Session End:
├─ All responses completed
├─ break exits event handler loop
├─ WebSocket closes
└─ Audio streams cleaned up
```

## Why This Works

### Event Processing Order:

1. **Request Phase** (`_send_text_message`):
   ```
   Client → Server: response.create with instructions
   ```

2. **Generation Phase** (Server side):
   ```
   Server: AI generates response
   Server: AI converts to audio
   ```

3. **Delivery Phase** (processed by event handler):
   ```
   Server → Client: response.created
   Server → Client: response.audio.delta (chunk 1)
   Server → Client: response.audio.delta (chunk 2)
   Server → Client: response.audio.delta (chunk 3)
   ...
   Server → Client: response.audio.done
   Server → Client: response.audio_transcript.done
   Server → Client: response.done ← WE TRACK THIS
   ```

The event handler **must keep running** to receive and process all these events, especially the `response.audio.delta` events that contain the actual audio data.

## Expected Behavior Now

When you run the interview:

1. ✅ Interview proceeds until ceiling
2. ✅ `trigger_assessment` called
3. ✅ Assessment report generated (~2-3 seconds)
4. ✅ Summary `response.create` sent
5. ✅ Goodbye `response.create` sent
6. ✅ **Event handler continues processing**
7. ✅ **Audio events received and processed** 🔊
8. ✅ **User HEARS the summary** 🔊
9. ✅ **User HEARS the goodbye** 🔊
10. ✅ Session ends after all audio completes

## Testing

```bash
cd korean_voice_tutor
uv run app.py
```

You should now:
- 🎤 Speak during interview
- 📊 Reach linguistic ceiling
- ⏳ Wait ~3 seconds for assessment generation
- 🔊 **HEAR the full assessment summary spoken**
- 🔊 **HEAR the goodbye message**
- ✅ Session ends cleanly

## Technical Notes

### Why Event-Driven Architecture Matters

The Realtime API uses an **event-driven architecture** where:
- Client sends requests (events)
- Server sends responses (events)
- Client must continuously process events to receive responses

This is different from request-response APIs where you make a call and wait for the response. With WebSockets and event-driven systems, you must keep the event processing loop running to receive asynchronous responses.

### Comparison to HTTP Request-Response:

**HTTP (Blocking):**
```python
response = requests.post("/api/speak", json={"text": "Hello"})
# Response arrives immediately
audio = response.content
play(audio)
```

**WebSocket Event-Driven (Non-Blocking):**
```python
# Send request
await websocket.send(json.dumps({"type": "response.create", ...}))

# Must keep processing events to receive response
async for event in websocket:  # ← MUST KEEP THIS RUNNING
    if event["type"] == "response.audio.delta":
        audio_chunk = event["delta"]
        play(audio_chunk)
```

The key insight: **You can't exit the event loop and expect to receive responses!**
