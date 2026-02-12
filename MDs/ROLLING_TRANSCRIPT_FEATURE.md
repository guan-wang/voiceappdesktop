# Rolling Transcript Feature ✅

## Feature Request

Auto-scroll AI transcript to display only the latest 3 lines, rolling up row by row as new messages arrive.

## Implementation

### Visual Behavior

**Before (single message):**
```
┌─────────────────────┐
│   Current Message   │
│   (single view)     │
└─────────────────────┘
```

**After (rolling 3 lines):**
```
┌─────────────────────┐
│ Old message (50%)   │ ← Oldest (faded)
│ Previous msg (70%)  │ ← Second oldest
│ Latest message ✨   │ ← Current (100% opacity)
└─────────────────────┘
```

When new message arrives, everything shifts up:
```
┌─────────────────────┐
│ Previous msg (50%)  │ ← Now oldest
│ Latest message (70%)│ ← Now second
│ New message! ✨     │ ← New current
└─────────────────────┘
```

### Key Changes

#### 1. CSS Structure (`style.css`)

**Container:**
```css
.ai-transcript {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: calc(1.6em * 3 + 24px); /* 3 lines + gaps */
    overflow: hidden;
}
```

**Individual Messages:**
```css
.ai-transcript-message {
    animation: slideUpFadeIn 0.4s ease-out;
    transition: opacity 0.3s ease;
}

/* Fade older messages for visual hierarchy */
.ai-transcript-message:not(:last-child) {
    opacity: 0.5; /* Oldest messages */
}

.ai-transcript-message:nth-last-child(2) {
    opacity: 0.7; /* Second newest */
}

/* Latest message is 100% opacity by default */
```

**Slide-up Animation:**
```css
@keyframes slideUpFadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

#### 2. JavaScript Logic (`app.js`)

**Track Messages:**
```javascript
// In constructor
this.aiMessages = []; // Keep last 3 messages
```

**Rolling Update:**
```javascript
streamAITranscript(text) {
    // Add new message
    this.aiMessages.push(text);
    
    // Keep only last 3
    if (this.aiMessages.length > 3) {
        this.aiMessages.shift(); // Remove oldest
    }
    
    // Rebuild view
    this.aiTranscript.innerHTML = '';
    this.aiMessages.forEach((msg, index) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'ai-transcript-message';
        
        if (index === this.aiMessages.length - 1) {
            // Stream latest message character by character
            streamCharacters(messageDiv, msg);
        } else {
            // Show older messages instantly
            messageDiv.textContent = msg;
        }
        
        this.aiTranscript.appendChild(messageDiv);
    });
}
```

### Visual Hierarchy

- **Latest message (100% opacity)**: Currently speaking, user's focus
- **Second message (70% opacity)**: Recent context
- **Oldest message (50% opacity)**: Background context

This creates a natural focus gradient, drawing attention to the latest message while keeping context visible.

### Responsive Design

**Desktop:**
- 3 lines @ 20px font, 1.6 line-height
- 12px gap between lines
- Total height: ~109px

**Mobile:**
- 3 lines @ 18px font, 1.5 line-height  
- 12px gap between lines
- Total height: ~105px

```css
@media (max-width: 480px) {
    .ai-transcript {
        max-height: calc(1.5em * 3 + 24px);
    }
    .ai-transcript-message {
        font-size: 18px;
        line-height: 1.5;
    }
}
```

### Smooth Transitions

1. **New message appears**: Slides up with fade-in (400ms)
2. **Opacity changes**: Old messages fade smoothly (300ms)
3. **Character streaming**: Latest message types out (20ms per char)
4. **Container overflow**: Hidden, no scrollbars

### User Experience

**Scenario 1: Normal Conversation**
```
Message 1: "안녕하세요! 저는 AI 선생님이에요."
[User speaks]
Message 2: "좋아요! 어디서 살아요?"
[User speaks]
Message 3: "서울이요? 재미있네요!"
```

Display shows:
```
Message 1 (faded 50%)
Message 2 (faded 70%)
Message 3 (typing... 100%) ✨
```

**Scenario 2: Assessment Summary**

Long assessment text will appear as a single message, wrapping within the 3-line container, automatically truncated if too long.

### Edge Cases Handled

✅ **Less than 3 messages**: Shows all, centered
✅ **Exactly 3 messages**: Perfect fit
✅ **More than 3 messages**: Auto-rolls, keeps latest 3
✅ **Very long message**: Wraps within container, may push out older messages visually
✅ **Rapid messages**: Each triggers animation smoothly

### Testing Checklist

- [x] New messages slide up smoothly
- [x] Only 3 messages visible at once
- [x] Latest message has full opacity
- [x] Older messages fade appropriately
- [x] Character streaming works on latest message
- [x] Older messages display instantly (no re-stream)
- [x] Mobile responsive (proper sizing)
- [x] No visual glitches or jumps

## Files Modified

- ✅ `web/frontend/style.css` - Rolling container, message styling, animations
- ✅ `web/frontend/app.js` - Message tracking, rolling logic

## No Breaking Changes

- User transcript: Unchanged (bottom, single message)
- Audio playback: Unchanged
- PTT functionality: Unchanged
- All existing features: Intact

**Pure additive feature** - improves transcript readability! 🎉

## Visual Demo Flow

```
1. AI: "Hello!"
   ┌─────────────┐
   │ Hello! ✨   │
   └─────────────┘

2. AI: "How are you?"
   ┌─────────────────┐
   │ Hello! (50%)    │
   │ How are you? ✨ │
   └─────────────────┘

3. AI: "What's your name?"
   ┌───────────────────────┐
   │ Hello! (50%)          │
   │ How are you? (70%)    │
   │ What's your name? ✨  │
   └───────────────────────┘

4. AI: "Nice to meet you!"
   ┌───────────────────────┐
   │ How are you? (50%)    │ ← "Hello!" rolled off
   │ What's your name? (70%)│
   │ Nice to meet you! ✨  │
   └───────────────────────┘
```

Always shows the most recent context!
