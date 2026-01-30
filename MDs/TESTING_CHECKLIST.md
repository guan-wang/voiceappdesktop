# Testing Checklist - Assessment Agent Optimizations

## Pre-Test Setup

### 1. Verify Files Created
```
✅ core/resources/system_prompt.txt          (New consolidated prompt)
✅ web/backend/shared_agents.py              (Shared instance)
✅ core/resources/README.md                  (Documentation)
✅ web/OPTIMIZATIONS_IMPLEMENTED.md          (Technical docs)
✅ OPTIMIZATION_SUMMARY.md                   (Quick summary)
```

### 2. Start the Server
```powershell
cd web/backend
.\start_server.ps1
```

**Expected output:**
```
📋 System prompt loaded (XXXX chars)
🔧 Initializing shared assessment agent...
✅ Shared assessment agent ready
🚀 Starting Korean Voice Tutor Web Server...
```

---

## Test 1: Basic Assessment Generation

### Steps:
1. Open browser to `https://localhost:7860`
2. Accept microphone permissions
3. Wait for "Ready to speak" message
4. Have a short conversation (2-3 exchanges)
5. Let AI detect ceiling and generate assessment

### Expected Behavior:
✅ Assessment starts within 1-2 seconds after ceiling detected  
✅ Console shows: "🚀 Calling OpenAI API with structured output..."  
✅ Assessment completes in ~2 seconds (faster than before)  
✅ Assessment summary is read aloud  
✅ JSON report saved in `web/backend/reports/`

### Verify:
- [ ] Assessment generated successfully
- [ ] Response time ~2 seconds (faster than ~2.5s before)
- [ ] No errors in console
- [ ] Report JSON contains all expected fields
- [ ] Audio readout works normally

---

## Test 2: Concurrent Sessions

### Steps:
1. Open 2-3 browser windows/tabs
2. Start conversations in all tabs simultaneously
3. Complete assessments in each tab

### Expected Behavior:
✅ All sessions work independently  
✅ Console shows "🔧 Initializing shared assessment agent..." ONLY ONCE  
✅ All subsequent sessions reuse the same agent  
✅ No performance degradation

### Verify:
- [ ] Multiple sessions work correctly
- [ ] Shared agent initialized once
- [ ] No conflicts between sessions
- [ ] Memory usage reasonable

---

## Test 3: Server Restart

### Steps:
1. Stop server (Ctrl+C)
2. Restart server
3. Run another assessment

### Expected Behavior:
✅ Server stops cleanly (within 5 seconds)  
✅ On restart, system prompt reloaded from file  
✅ Assessment works normally

### Verify:
- [ ] Server stops without hanging
- [ ] Restart successful
- [ ] System prompt loaded
- [ ] Assessment works after restart

---

## Test 4: Edit System Prompt (Optional)

### Steps:
1. Stop server
2. Open `core/resources/system_prompt.txt`
3. Add a comment at the top: "### TEST EDIT - Remove this line"
4. Save file
5. Restart server
6. Check console output

### Expected Behavior:
✅ Console shows "📋 System prompt loaded (XXXX chars)" with new size  
✅ New prompt takes effect immediately

### Verify:
- [ ] File edits detected
- [ ] Prompt reloaded successfully
- [ ] Changes applied to assessments

---

## Test 5: Error Handling

### Steps:
1. Test with very short conversation (1 exchange)
2. Test with long conversation (10+ exchanges)

### Expected Behavior:
✅ Short conversations handled gracefully  
✅ Long conversations don't timeout  
✅ Assessment quality unchanged

### Verify:
- [ ] No crashes with edge cases
- [ ] Error messages clear (if any)
- [ ] Assessments maintain quality

---

## Performance Benchmarks

### Before Optimization:
- API calls: 2 per assessment
- Response time: ~2600ms
- Tokens: ~5300

### After Optimization (Target):
- API calls: 1 per assessment ✅
- Response time: ~2100ms ✅
- Tokens: ~5000 ✅

### Measure:
1. Run 5 assessments
2. Note response times
3. Check OpenAI API dashboard for token counts

### Record Results:

**Assessment 1:** _____ ms  
**Assessment 2:** _____ ms  
**Assessment 3:** _____ ms  
**Assessment 4:** _____ ms  
**Assessment 5:** _____ ms  

**Average:** _____ ms (Target: ~2100ms)

---

## Console Output Verification

### Expected logs during assessment:

```
📊 Assessment Agent starting analysis...
🚀 Calling OpenAI API with structured output...
✅ Assessment report generated successfully
```

### Should NOT see:
❌ "🔧 Agent is calling tools..."  
❌ "🔧 Tool called: read_guidance"  
❌ "✅ Guidance text loaded"  

(These are from old tool calling approach - should be gone!)

---

## Troubleshooting

### Problem: "File not found" error for system_prompt.txt

**Check:**
1. File exists at `core/resources/system_prompt.txt`
2. Working directory is correct
3. File permissions allow reading

**Fix:**
```powershell
cd korean_voice_tutor
ls core/resources/system_prompt.txt
```

### Problem: Assessment slower than expected

**Check:**
1. Network latency to OpenAI
2. OpenAI API rate limits
3. File size of system_prompt.txt

**Fix:**
- Check file size: should be ~6KB
- If much larger, edit for conciseness

### Problem: "Module not found" error for shared_agents

**Check:**
1. File exists: `web/backend/shared_agents.py`
2. Import paths correct

**Fix:**
```python
# In realtime_bridge.py, verify line exists:
from shared_agents import get_assessment_agent
```

---

## Success Criteria

All checks passed:

- [x] No linter errors
- [ ] Server starts successfully
- [ ] System prompt loads correctly
- [ ] Assessments generate successfully
- [ ] Response time ~2 seconds (20% improvement)
- [ ] Single API call per assessment
- [ ] Concurrent sessions work
- [ ] Server restart clean
- [ ] No breaking changes
- [ ] Same assessment quality

---

## Post-Test Actions

### If all tests pass:
1. ✅ Mark optimizations as production-ready
2. ✅ Deploy to production environment
3. ✅ Monitor performance metrics
4. ✅ Celebrate 20% performance improvement! 🎉

### If any tests fail:
1. ⚠️ Note specific failures
2. ⚠️ Check error messages
3. ⚠️ Review code changes
4. ⚠️ Rollback if necessary (low risk)

---

## Additional Notes

- Old tool calling code removed: ~80 lines simpler
- System prompt now easy to edit: `core/resources/system_prompt.txt`
- Shared agent pattern improves scalability
- No changes to assessment output format
- Backward compatible with existing reports

---

**Ready to test! Run through checklist and mark items as you verify them.** ✅
