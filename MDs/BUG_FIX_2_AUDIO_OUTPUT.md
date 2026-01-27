# Bug Fix #2 - Assessment Summary Not Being Spoken

## The Problem

After the assessment was successfully generated, the verbal summary and goodbye message were not spoken to the user via audio. The terminal showed:

```
🗣️ Sending assessment summary to be spoken...
👋 Sending goodbye message...
✅ Assessment complete. Ending session...
```

But the user heard nothing.

## Root Cause

The `_send_text_message` method was using an **incorrect message format** for the OpenAI Realtime API.

### Wrong Approach (Attempted):
```python
async def _send_text_message(self, websocket, text: str):
    message_event = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "assistant",      # ❌ Can't directly create assistant messages
            "content": [
                {
                    "type": "input_text",  # ❌ Wrong content type
                    "text": text
                }
            ]
        }
    }
    # ...
```

**Problem**: The Realtime API doesn't support directly injecting assistant messages to be spoken. It needs either:
1. User messages that prompt the AI
2. `response.create` with instructions

## The Fix

### Solution: Use `response.create` with `instructions`

**After:**
```python
async def _send_text_message(self, websocket, text: str):
    """Send a text message for the AI to speak using response.create with instructions."""
    # Use response.create with instructions to make the AI say the exact text
    response_event = {
        "type": "response.create",
        "response": {
            "modalities": ["text", "audio"],
            "instructions": f"Say exactly this to the user: {text}"
        }
    }
    await websocket.send(json.dumps(response_event))
```

This tells the Realtime API to create a response where the AI speaks the exact text we provide.

## Additional Improvements

### 1. Increased Wait Times

Assessment summaries can be lengthy (5-6 sentences), so wait times were increased:

**Before:**
```python
await asyncio.sleep(8)  # Assessment summary
await asyncio.sleep(3)  # Goodbye
```

**After:**
```python
await asyncio.sleep(15)  # Assessment summary - longer for detailed content
await asyncio.sleep(5)   # Goodbye - slightly longer
```

### 2. Added Progress Messages

```python
print("⏳ Waiting for assessment summary to be spoken (15 seconds)...")
# ...
print("⏳ Waiting for goodbye message (5 seconds)...")
```

This gives the user feedback about what's happening.

## How It Works Now

1. **Assessment Generated** → Structured report created
2. **Convert to Verbal Summary** → Friendly, conversational text
3. **Send via Realtime API** → `response.create` with instructions
4. **AI Speaks Summary** → Audio output via Realtime API (15 seconds)
5. **Send Goodbye** → `response.create` with instructions  
6. **AI Speaks Goodbye** → Audio output (5 seconds)
7. **Session Ends** → Clean exit

## Expected Behavior

When you run the interview now:

1. ✅ Interview proceeds until linguistic ceiling
2. ✅ `trigger_assessment` function called
3. ✅ Assessment agent analyzes transcript
4. ✅ Structured report generated and saved
5. ✅ **Verbal summary SPOKEN to user via audio** 🔊
6. ✅ **Goodbye message SPOKEN to user via audio** 🔊
7. ✅ Session ends gracefully

## Testing

Run the interview again:
```bash
cd korean_voice_tutor
uv run app.py
```

You should now **hear**:
- The full assessment summary spoken in a natural voice
- The goodbye message
- Then the session ends

## Technical Notes

### Why `instructions` in `response.create`?

The Realtime API's `response.create` event supports an `instructions` parameter that overrides the session-level instructions for that specific response. This allows us to tell the AI exactly what to say without modifying the conversation history.

### Alternative Approaches Considered

1. **User message prompts** - Would work but adds extra wrapper text
2. **Direct audio injection** - Not supported by Realtime API
3. **Text-to-speech separately** - Would require separate TTS API, inconsistent voice

The `instructions` approach is the cleanest and most aligned with the Realtime API design.
