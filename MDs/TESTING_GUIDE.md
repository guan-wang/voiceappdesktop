# Testing Guide - Visual Report Implementation

## Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key set in `.env` file

### Run the Server
```bash
cd volley/voiceappdesktop/web/backend
python server.py
```

The server will start on `http://localhost:8000`

### Testing Steps

#### 1. Basic Flow Test
1. Open browser to `http://localhost:8000`
2. Click "Start Learning" button
3. Allow microphone access
4. Hold mic button and speak in Korean (have a conversation)
5. Wait for AI to trigger assessment
6. Observe loading overlay: "Generating report"
7. **New**: Visual report should appear (full screen)
8. **New**: AI audio should play in background
9. **New**: Click "Begin Path" button
10. **New**: Audio should stop immediately
11. Survey should appear

#### 2. Visual Report Elements Test
When report appears, verify:

**Header Section**
- [ ] Title: "Proficiency Report"
- [ ] Subtitle: "Korean Assessment • [Date]"
- [ ] Reference ID (e.g., "REF: 9aead39e")

**Left Column**
- [ ] Large circular badge with CEFR level (e.g., "B1")
- [ ] Level description (e.g., "B1 (Intermediate)")
- [ ] Progress bar with all levels (A1, A2, B1, B2, C1, C2)
- [ ] Progress bar fills to correct position
- [ ] Active level is highlighted in violet
- [ ] Ceiling analysis card shows phase and text

**Right Column**
- [ ] "Skill Analysis" section header with violet indicator
- [ ] Radar chart displays with 5 axes
- [ ] All 5 domains labeled: Fluency, Grammar, Lexical, Phonology, Coherence
- [ ] Polygon filled with violet color
- [ ] Data points visible on chart
- [ ] 5 domain cards below chart
- [ ] Each card shows domain name and rating bars (1-5)
- [ ] Cards are clickable

**Domain Cards**
- [ ] Click a card to expand
- [ ] Expanded card shows:
  - Background changes to violet tint
  - Border becomes violet
  - Observation text appears
  - Evidence section with Korean text
  - Chevron icon rotates 180°
- [ ] Click again to collapse
- [ ] Multiple cards can be expanded simultaneously

**Strategy Section**
- [ ] "Optimization Focus" badge visible
- [ ] "Recommended Strategy" title
- [ ] Strategy description text
- [ ] "Target Curriculum" label and module text
- [ ] "Begin Path" button (violet, prominent)

**Footer**
- [ ] "Seoul Night • Language Assessment Engine" text

#### 3. Audio Behavior Test
- [ ] AI starts speaking when report appears
- [ ] Report is visible while audio plays
- [ ] Audio continues if you scroll the report
- [ ] Clicking "Begin Path" stops audio immediately
- [ ] No audio glitches or overlapping sounds

#### 4. Transition Test
- [ ] Loading overlay fades out smoothly
- [ ] Report fades in smoothly
- [ ] Report fades out when CTA clicked
- [ ] Survey fades in after report

#### 5. Mobile Responsive Test
Open on mobile device or use browser dev tools (mobile view):
- [ ] Single column layout
- [ ] Badge section displays correctly
- [ ] Radar chart is visible and sized properly
- [ ] Domain cards are touch-friendly
- [ ] CTA button is full width
- [ ] Text is readable (not too small)
- [ ] Scrolling works smoothly

#### 6. Korean Text Test
- [ ] Korean text in evidence sections displays correctly
- [ ] Font is readable (Noto Sans KR)
- [ ] No character encoding issues

#### 7. Edge Cases
- [ ] Report works with all CEFR levels (A1, A2, B1, B2, C1, C2)
- [ ] Report works with different numbers of domains
- [ ] Long strategy text wraps properly
- [ ] Long evidence quotes display well

## Common Issues & Solutions

### Issue: Report doesn't appear
**Check:**
- Browser console for JavaScript errors
- Network tab for failed script loads
- Verify all scripts are loaded: audio.js, report.js, app.js

### Issue: Radar chart doesn't render
**Check:**
- Browser supports SVG
- Console for SVG-related errors
- Domain data is properly structured

### Issue: Korean text displays as boxes
**Check:**
- Google Fonts link is in `<head>`
- Network tab shows font loaded successfully
- Font family applied in CSS

### Issue: Audio doesn't stop when CTA clicked
**Check:**
- AudioManager.clearQueue() is being called
- Console logs confirm CTA handler executed
- No JavaScript errors in console

### Issue: Styling looks broken
**Check:**
- style.css loaded correctly
- CSS selector names match HTML
- Browser supports CSS Grid and Flexbox

## Browser Console Tests

Open browser console and run:

### Check if ReportRenderer exists
```javascript
console.log(typeof ReportRenderer); // Should be 'function'
```

### Check if KoreanVoiceTutor has reportRenderer
```javascript
// After app starts
console.log(window.app?.reportRenderer); // Should be object
```

### Manually trigger report (for testing)
```javascript
// Create test data
const testData = {
    session_id: "test-12345",
    timestamp: new Date().toISOString(),
    report: {
        proficiency_level: "B1 (Intermediate)",
        ceiling_phase: "Probe",
        ceiling_analysis: "Test ceiling analysis text",
        domain_analyses: [
            { domain: "Fluency", rating: 4, observation: "Good fluency", evidence: "테스트 증거" },
            { domain: "Grammar", rating: 3, observation: "Some errors", evidence: "문법 증거" },
            { domain: "Lexical", rating: 3, observation: "Adequate vocabulary", evidence: "어휘 증거" },
            { domain: "Phonology", rating: 4, observation: "Clear pronunciation", evidence: "발음 증거" },
            { domain: "Coherence", rating: 3, observation: "Generally coherent", evidence: "일관성 증거" }
        ],
        starting_module: "Test Module Name",
        optimization_strategy: "Test strategy description here"
    }
};

// Show report manually
window.app.reportRenderer.showReport(testData);
```

## Performance Checks

### Page Load
- Initial page load should be fast (<2s)
- All scripts should load quickly
- No blocking resources

### Report Rendering
- Report should appear within 500ms after assessment_complete
- Animations should be smooth (60fps)
- No layout shifts or jank

### Memory Usage
- Open browser dev tools → Performance → Memory
- Record while showing/hiding report
- Check for memory leaks
- Report should not significantly increase memory

## Accessibility Testing

### Keyboard Navigation
- [ ] Can tab through domain cards
- [ ] Enter key expands/collapses cards
- [ ] Can focus CTA button with keyboard
- [ ] Enter or Space activates CTA button

### Screen Reader (Optional)
- Text content should be readable
- Sections should have logical structure
- Interactive elements announced properly

## Success Criteria

The implementation is successful if:
1. ✅ Report displays after assessment completes
2. ✅ All visual elements render correctly
3. ✅ Radar chart displays with correct data
4. ✅ AI audio plays in background
5. ✅ CTA button stops audio and shows survey
6. ✅ No JavaScript errors in console
7. ✅ Responsive design works on mobile
8. ✅ Korean text displays correctly
9. ✅ Smooth transitions and animations
10. ✅ Survey flow continues as expected

## Debugging Tips

### Enable verbose logging
Add to app.js constructor:
```javascript
this.debug = true;
```

### Log report data
In assessment_complete handler:
```javascript
console.log('Report data:', JSON.stringify(message.report, null, 2));
```

### Check SVG rendering
In browser console:
```javascript
document.querySelector('#radarChart').innerHTML;
```

### Inspect audio state
```javascript
console.log('Audio playing:', window.app.audioManager.isPlaying);
console.log('Audio queue:', window.app.audioManager.audioQueue.length);
```

## Rollback Plan

If issues occur, to revert to previous behavior:

1. Comment out report renderer instantiation in app.js:
   ```javascript
   // this.reportRenderer = new ReportRenderer();
   ```

2. Revert assessment_complete handler to previous version

3. Remove report.js script tag from index.html

4. Report CSS can remain (won't affect anything if not used)

The app will fall back to streaming text behavior.
