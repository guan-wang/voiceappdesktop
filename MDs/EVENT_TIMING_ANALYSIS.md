# Event Timing Analysis - Why Events Weren't Firing

## The Bug

From the terminal output:
```
⏳ Waiting for acknowledgment audio to complete...
⚠️ Timeout waiting for ack audio, proceeding anyway
```

The `response.audio_transcript.done` event WAS firing (it's in the event list), but our handler wasn't catching it!

## Root Cause: Counter Logic Error

### What Was Happening (BROKEN):

```
1. trigger_assessment called
   pending = 1
   completed = 0
   
2. AI generates acknowledgment response

3. response.done fires (ACK)
   completed++ → completed = 1  ← Incremented FIRST
   Check: if completed == 1 → Generate assessment
   
4. response.audio_transcript.done fires (ACK)  ← Fires AFTER response.done
   completed = 1  ← Already 1!
   Check: if completed == 0 → FALSE!  ← NEVER MATCHES!
   ack_audio_done NOT set → Timeout!
```

**The Problem**: We incremented `completed` in `response.done`, but then checked `completed` in the audio handler. By the time the audio event fires, `completed` is already incremented, so the check fails!

### Event Order (from API):

```
response.created
response.audio.delta
response.audio.done
response.audio_transcript.delta
response.audio_transcript.done  ← This one!
response.done                    ← This one fires LAST!
```

**But we process them in this order**:
```
response.done                    ← We process this first (increment counter)
response.audio_transcript.done   ← Then this fires (counter already incremented!)
```

No wait, that's not right. Let me check the actual order...

Actually, looking at the API docs and our event handler, `response.audio_transcript.done` fires BEFORE `response.done`. So the issue is different.

Let me trace again with the CORRECT order:

```
1. trigger_assessment called
   pending = 1
   completed = 0
   
2. AI starts generating acknowledgment

3. response.audio_transcript.done fires (ACK)
   pending = 1
   completed = 0  ← Still 0
   Check: if completed == 0 → Set ack flag  ← Should work!
   
4. response.done fires (ACK)
   completed++ → completed = 1
   Waits for ack flag (should already be set)
```

Hmm, this SHOULD work. Let me check if maybe the event isn't being matched correctly...

## Actual Problem: Event Matching

Looking at the logs more carefully:

```
🔧 [DEBUG] All event types received: [...'response.audio_transcript.done'...]
```

The event IS firing! But we're not seeing "✅ Acknowledgment audio complete" in the logs.

This means our handler condition is failing:
```python
if self.assessment_triggered:
    if self.assessment_responses_completed == 0:
        print("✅ Acknowledgment audio complete")
```

Wait! I see it now. Looking at the logs:

```
✅ Response complete (ID: unknown)
📊 Assessment response 1/1 completed (Acknowledgment)
```

This happens IMMEDIATELY after trigger_assessment. The response.done fires right away!

Then later:
```
🤖 AI: 평가를 준비하고 있습니다. 잠시만 기다려 주세요.
```

The AI speaks the acknowledgment AFTER we've already incremented the counter!

## The Real Issue: Response Order

The tool output IS a response! So:

1. trigger_assessment called → sends tool output
2. response.done fires for TOOL OUTPUT → completed = 1  ← This happens immediately!
3. AI generates speech response
4. response.audio_transcript.done fires → completed already 1 → doesn't match!

The tool output response completes immediately (no audio), then the AI generates the spoken response.

## The Fix

We need to check based on PENDING (what we're waiting for) not COMPLETED (what's done):

```python
if self.assessment_responses_pending == 1:
    # We just sent/are sending acknowledgment
    self.ack_audio_done.set()
elif self.assessment_responses_pending == 2:
    # We just sent/are sending summary
    self.summary_audio_done.set()
```

This way:
- When ack speech plays: pending = 1 → matches ✓
- When summary speech plays: pending = 2 → matches ✓
- When goodbye speech plays: pending = 3 → matches ✓
