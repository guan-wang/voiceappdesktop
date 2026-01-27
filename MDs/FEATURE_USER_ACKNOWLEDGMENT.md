# Feature: User Acknowledgment Detection

## Overview

The interview agent now detects when the user acknowledges receiving the assessment report or says goodbye during the assessment delivery phase, allowing for a more natural and responsive session ending.

## How It Works

### Dual Exit Conditions

The session can now end in **two ways** during assessment delivery:

#### 1. **Automatic Exit** (Original)
- System sends 2 responses (assessment summary + goodbye)
- Event handler tracks `response.done` events
- After both responses complete → Session ends
- **Timeout**: ~20 seconds (15s for summary + 5s for goodbye)

#### 2. **User-Triggered Exit** (New) ⭐
- User says acknowledgment keyword during assessment
- System detects it immediately
- Session ends gracefully without waiting for full playback
- **Faster**: Ends as soon as user acknowledges

### Detection Logic

When user speaks during assessment delivery:

```python
User: "감사합니다" (Thank you)
       ↓
_is_user_acknowledgment() checks keywords
       ↓
Match found! → user_acknowledged_report = True
       ↓
Session ends gracefully
```

## Supported Keywords

### Korean Keywords 🇰🇷

**Thank You:**
- `감사합니다` - Thank you (formal)
- `감사` - Thanks
- `고마워` - Thanks (informal)
- `고맙습니다` - Thank you (formal)
- `수고하세요` - Thank you for your work

**Understanding:**
- `알겠습니다` - I understand (formal)
- `알겠어요` - I understand (polite)
- `알았어요` - Got it
- `네, 알겠습니다` - Yes, I understand

**Goodbye:**
- `안녕히` - Goodbye (part of phrases)
- `안녕` - Bye
- `잘 가` - Bye (informal)

**Acceptance:**
- `좋아요` - Good/Okay
- `괜찮아요` - It's okay/good

### English Keywords 🇺🇸

(In case user switches to English)

- `thank`, `thanks`
- `bye`, `goodbye`, `see you`
- `got it`, `understand`
- `okay`, `ok`
- `great`, `good`

## Implementation Details

### 1. New Instance Variables

```python
self.user_acknowledged_report = False  # Tracks if user acknowledged
```

### 2. Acknowledgment Detection Method

```python
def _is_user_acknowledgment(self, transcript: str) -> bool:
    """Check if user acknowledged or said goodbye."""
    # Normalize and check against keyword lists
    # Returns True if any keyword matches
```

### 3. Event Handler Integration

```python
elif event_type == "conversation.item.input_audio_transcription.completed":
    transcript = event.get("transcript", "")
    
    if self.assessment_triggered:
        # Check for acknowledgment during assessment
        if self._is_user_acknowledgment(transcript):
            print("✅ User acknowledged the report")
            self.user_acknowledged_report = True
            # End session immediately
            self.should_end_session = True
            break
```

### 4. Response.Done Handler

```python
elif event_type == "response.done":
    if self.assessment_triggered:
        # Check BOTH conditions
        if (completed >= pending) or self.user_acknowledged_report:
            # End session
            break
```

## User Experience Scenarios

### Scenario 1: Patient User (Automatic Exit)

```
AI: "Based on our conversation, I've assessed your Korean proficiency at A2 level..."
    [User listens silently]
AI: "You performed well during the Level-Up phase..."
    [User listens silently]
AI: "Thank you for completing the interview! Goodbye!"
    [15 seconds pass]
System: ✅ All assessment responses completed. Ending session...
```

**Total Time:** ~20 seconds

### Scenario 2: Impatient User (User-Triggered Exit) ⭐

```
AI: "Based on our conversation, I've assessed your Korean proficiency at A2 level..."
User: "감사합니다!" (Thank you!)
System: ✅ User acknowledged the report or said goodbye
System: 👋 User acknowledged. Ending session gracefully...
```

**Total Time:** ~3 seconds (much faster!)

### Scenario 3: Early Acknowledgment

```
AI: "Based on our conversation..."
User: "Okay, got it!"
System: ✅ User acknowledged
System: [Ends session immediately, doesn't wait for goodbye message]
```

**Total Time:** ~2 seconds

## Benefits

### 1. **Improved User Experience**
- Users don't have to wait through lengthy assessment if they're satisfied
- More natural conversation flow
- Respects user's time

### 2. **Flexibility**
- Power users can end quickly
- Beginners can listen to everything
- Both experiences are supported

### 3. **Natural Interaction**
- Mimics real human-to-human conversation
- People naturally say "thanks" or "okay" when they've heard enough
- System responds appropriately

### 4. **Efficiency**
- Saves ~15-18 seconds for users who acknowledge early
- Reduces API costs (less audio generation/transmission)

## Technical Considerations

### Race Condition Handling

The system handles potential race conditions:

```python
# Both conditions are checked
if (completed >= pending) or self.user_acknowledged_report:
    # Whichever happens first triggers the exit
```

### No Duplicate Exits

The `should_end_session` flag prevents duplicate cleanup:

```python
if not self.should_end_session:
    self.should_end_session = True
    # Cleanup only happens once
```

### Graceful Degradation

If keyword detection fails:
- Automatic timeout still works
- Session ends after ~20 seconds
- No hanging or infinite loops

## Testing

### Test Case 1: Say "Thank You" During Summary

```bash
cd korean_voice_tutor
uv run app.py

# During interview:
You: [Speak Korean until ceiling]
AI: [Triggers assessment]
AI: "Based on our conversation..."
You: "감사합니다!"
Expected: Session ends immediately ✅
```

### Test Case 2: Say Nothing (Automatic)

```bash
# During assessment:
AI: [Speaks full summary]
AI: [Speaks goodbye]
You: [Silent]
Expected: Session ends after ~20 seconds ✅
```

### Test Case 3: Say "Okay" Early

```bash
# During assessment:
AI: "Based on our..."
You: "Okay!"
Expected: Session ends immediately ✅
```

### Test Case 4: Say Unrelated Phrase

```bash
# During assessment:
AI: "You performed well..."
You: "너무 어려워요" (It's too hard)
Expected: Session continues (not an acknowledgment) ✅
```

## Future Enhancements

### Potential Improvements:

1. **Sentiment Analysis**
   - Detect negative responses ("I disagree")
   - Allow user to request re-assessment

2. **Confirmation Prompt**
   - AI: "Would you like me to save your report?"
   - User: "Yes" → Save and end

3. **Summary Level Control**
   - User: "Short version please"
   - AI: Provides condensed summary

4. **Multi-language Support**
   - Expand keyword lists for other languages
   - Auto-detect language switches

## Keyword List Maintenance

To add new keywords, update the lists in `_is_user_acknowledgment()`:

```python
korean_keywords = [
    "your_new_keyword",  # Your comment
    # ...
]
```

**Guidelines for adding keywords:**
- Use common, natural phrases
- Include both formal and informal versions
- Test with native speakers
- Avoid ambiguous words (words with multiple meanings)
