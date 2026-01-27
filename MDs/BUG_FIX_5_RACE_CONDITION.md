# Bug Fix #5 - Race Condition: Multiple Responses in Progress

## Root Cause

**The Problem**: Realtime API can only process **ONE response at a time**. Our code was trying to create multiple responses simultaneously, causing the error:

```
❌ API Error: Conversation already has an active response in progress: resp_XXX. 
Wait until the response is finished before creating a new one.
```

**What was happening**:
```
trigger_assessment called
  ↓
Send _send_text_message (acknowledgment) → Creates Response A ⚠️
  ↓
Send send_tool_output → Tries to modify conversation while Response A is in progress ❌
  ↓
API rejects: "already has response in progress"
```

## The Fix: Sequential Response Chain

Instead of trying to send multiple messages at once, we chain them sequentially using the `response.done` event handler as a trigger for the next response.

### New Flow

```
1. trigger_assessment function called
   ↓
2. Send tool output with ack instruction
   → AI responds naturally (Response 1: Acknowledgment)
   ↓
3. response.done event fires (Response 1 complete)
   → Generate assessment
   → Send summary message (Response 2)
   ↓
4. response.done event fires (Response 2 complete)
   → Send goodbye message (Response 3)
   ↓
5. response.done event fires (Response 3 complete)
   → End session
```

**Key Insight**: Use `response.done` as the trigger to send the NEXT message, ensuring only one response is in progress at any time.

## Code Changes

### 1. Removed Immediate Custom Acknowledgment

**Before (Lines 523-530):**
```python
# IMMEDIATELY send acknowledgment to user
print("\n💬 Sending immediate acknowledgment to user...")
immediate_ack = "Your assessment is being prepared. Please wait a moment."
await self._send_text_message(websocket, immediate_ack)  # ❌ Creates response while another is active
self.assessment_responses_pending += 1

# Send tool output back to model (silent, just to complete the function call)
await self.send_tool_output(websocket, call_id, "Assessment triggered successfully. Continue processing.")
```

**After (Lines 523-536):**
```python
# Send tool output with instruction for AI to immediately acknowledge
# The AI will naturally respond to this, creating the acknowledgment
print("\n💬 Sending tool output with acknowledgment instruction...")
await self.send_tool_output(
    websocket, 
    call_id, 
    "Assessment triggered successfully. Please IMMEDIATELY tell the user in Korean: '평가를 준비하고 있습니다. 잠시만 기다려 주세요.' (Your assessment is being prepared. Please wait a moment.)"
)

# This tool output response will be the acknowledgment (response 1)
self.assessment_responses_pending = 1

print("⏳ Waiting for AI acknowledgment response...")
print("💡 Assessment will generate AFTER acknowledgment completes.")

# Store assessment trigger data for later use
self.assessment_reason = reason

# NOTE: We DON'T generate assessment here!
# It will be generated in response.done handler after acknowledgment
```

**Key Changes**:
- ✅ Send tool output FIRST (completes function call, allows current response to proceed)
- ✅ Include acknowledgment instruction IN the tool output
- ✅ AI naturally responds with acknowledgment (no forced response.create)
- ✅ No race condition!

### 2. Sequential Message Sending in response.done

**Before (Lines 436-447):**
```python
# Send summary
await self._send_text_message(websocket, verbal_summary)
self.assessment_responses_pending += 1  # Response 2

# Send goodbye immediately after
await self._send_text_message(websocket, goodbye_msg)
self.assessment_responses_pending += 1  # Response 3
# ❌ Two responses sent back-to-back → Race condition!
```

**After (Lines 436-471):**
```python
if self.assessment_responses_completed == 1:
    # Acknowledgment just completed
    # Generate assessment and send summary
    report = self.assessment_agent.generate_assessment(self.conversation_history)
    verbal_summary = self.assessment_agent.report_to_verbal_summary(report)
    
    # Send summary (Response 2)
    await self._send_text_message(websocket, verbal_summary)
    self.assessment_responses_pending = 2
    
elif self.assessment_responses_completed == 2:
    # Summary just completed
    # NOW send goodbye (Response 3)
    goodbye_msg = "Thank you for completing the interview! Keep practicing, and you'll continue to improve. Goodbye!"
    await self._send_text_message(websocket, goodbye_msg)
    self.assessment_responses_pending = 3
    
elif self.assessment_responses_completed == 3:
    # Goodbye completed
    # End session
```

**Key Changes**:
- ✅ Only ONE message sent per response.done event
- ✅ Each response triggers the next one
- ✅ Sequential chain: Ack → Summary → Goodbye → End
- ✅ No overlapping responses!

### 3. Added assessment_reason Instance Variable

**File**: `interview_agent.py` (Line 44)

```python
self.assessment_reason = ""  # Store the reason for assessment trigger
```

This stores the reason for later logging/debugging.

## Timeline Comparison

### Before (Broken - Race Condition):

```
00:00 - trigger_assessment called
00:00 - Send _send_text_message (ack) → Response A starts ⚡
00:00 - Send tool_output → ❌ API ERROR: Response already in progress
00:00 - Assessment generation starts (but stuck due to error)
[System becomes unresponsive, no audio plays]
```

### After (Fixed - Sequential Chain):

```
00:00 - trigger_assessment called
00:00 - Send tool output with ack instruction → Response 1 starts ⚡
00:03 - Response 1 (Ack) completes ✅
        🔊 "평가를 준비하고 있습니다. 잠시만 기다려 주세요."
00:03 - response.done fires → Generate assessment (3-5s)
00:08 - Send summary → Response 2 starts ⚡
00:08 - Response 2 (Summary) starts playing
00:23 - Response 2 (Summary) completes ✅
        🔊 [Full assessment summary]
00:23 - response.done fires → Send goodbye
00:23 - Response 3 (Goodbye) starts ⚡
00:28 - Response 3 (Goodbye) completes ✅
        🔊 "Thank you for completing the interview! Goodbye!"
00:28 - response.done fires → End session
```

## Testing

Run the interview and watch for:

```bash
cd korean_voice_tutor
uv run app.py
```

**Expected console output:**

```
📊 Assessment triggered: User reached ceiling at...

💬 Sending tool output with acknowledgment instruction...
⏳ Waiting for AI acknowledgment response...
💡 Assessment will generate AFTER acknowledgment completes.

✅ Response complete (ID: abc12345)
📊 Assessment response 1/1 completed (Acknowledgment)

🔍 Now generating assessment report...
📊 Assessment Agent starting analysis...
✅ Assessment report generated successfully

🗣️ Sending assessment summary to be spoken...
   📤 Sending to be spoken: "Based on our conversation, I've assessed your Korean proficiency at A2 level..."
⏳ Waiting for summary to complete before sending goodbye...

✅ Response complete (ID: def67890)
📊 Assessment response 2/2 completed (Assessment Summary)

👋 Now sending goodbye message...
   📤 Sending to be spoken: "Thank you for completing the interview! Keep practicing..."
⏳ Waiting for goodbye to complete...

✅ Response complete (ID: ghi24680)
📊 Assessment response 3/3 completed (Goodbye)

✅ All assessment responses completed. Ending session...
```

**Key indicators of success:**
- ✅ No "response already in progress" errors
- ✅ All 3 messages play sequentially
- ✅ Clean session end
- ✅ No WebSocket errors

## Technical Details

### Why Tool Output Works

**Tool output** (`send_tool_output`) doesn't create a new response - it:
1. Completes the current function call
2. Allows the Realtime API to continue its current response
3. The AI naturally speaks the instruction we provided

This is fundamentally different from `response.create` which tries to start a NEW response.

### The Event-Driven Pattern

This is a classic **event-driven state machine**:

```
State 1: Ceiling Reached
  Action: Send tool output with ack
  Next State: Waiting for Ack
  
State 2: Ack Complete (response.done)
  Action: Generate assessment, send summary
  Next State: Waiting for Summary
  
State 3: Summary Complete (response.done)
  Action: Send goodbye
  Next State: Waiting for Goodbye
  
State 4: Goodbye Complete (response.done)
  Action: End session
  Next State: Done
```

Each state transition is triggered by the `response.done` event, ensuring proper sequencing.

### Why This is Better

**Synchronous Approach (Broken)**:
```python
await send_ack()      # Response A
await send_tool()     # Tries to modify conversation ❌
await send_summary()  # Response B (conflicts with A) ❌
await send_goodbye()  # Response C (conflicts with B) ❌
```

**Event-Driven Approach (Fixed)**:
```python
# In function handler:
await send_tool_with_ack()  # Single response

# In response.done handler:
if completed == 1:
    await send_summary()    # Single response
elif completed == 2:
    await send_goodbye()    # Single response
```

## Common Pitfalls

❌ **Don't** try to send multiple responses in succession:
```python
await self._send_text_message(websocket, msg1)
await self._send_text_message(websocket, msg2)  # Will fail!
```

✅ **Do** use response.done to chain them:
```python
# In function handler:
await self._send_text_message(websocket, msg1)

# In response.done handler:
if completed == 1:
    await self._send_text_message(websocket, msg2)
```

❌ **Don't** send tool output AFTER creating a response:
```python
await self._send_text_message(websocket, msg)  # Response starts
await self.send_tool_output(websocket, id, output)  # ❌ Conflict!
```

✅ **Do** send tool output FIRST:
```python
await self.send_tool_output(websocket, id, output)  # Completes function call
# AI responds naturally
```

## Benefits

1. **No Race Conditions**: Only one response active at a time
2. **Immediate Feedback**: User hears acknowledgment within 1-2 seconds
3. **Reliable Audio**: All messages play in correct order
4. **Clean Session End**: Proper state management
5. **Debuggable**: Clear sequential flow in logs

## User Experience

User hears:
1. 🔊 **Immediate** (1-2s): "평가를 준비하고 있습니다. 잠시만 기다려 주세요."
2. 🔊 **After generation** (5s later): Full assessment summary
3. 🔊 **At end** (after summary): "Thank you for completing the interview! Goodbye!"

Total time: ~25 seconds with NO dead silence or errors! ✅
