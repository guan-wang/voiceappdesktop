# Core Resources

This directory contains shared resources used by the interview and assessment agents.

## Files

### `interview_system_prompt.txt`
**Purpose:** Canonical system prompt for the interview agent (web and desktop).
- 3-phase WLP structure (Warm-up, Level-up, Probe)
- Korean-specific questions and elicitation strategies
- Loaded via `core.prompt_loader.load_interview_system_prompt()`

### `system_prompt.txt`
**Purpose:** Complete system prompt for the assessment agent, including:
- Identity and role definition
- Full SSOI assessment protocol
- Evaluation rubrics and scoring logic
- Task sequence and instructions
- Report generation schema

**Size:** ~1,400 tokens (~6KB)

**Editing:** You can directly edit this file to modify the assessment protocol or instructions. Changes will take effect after server restart.

**Capacity:** Current usage is only 1% of OpenAI's context window. You can safely expand this file by 2-10x without performance issues.

---

## How System Prompt Loading Works

1. **First server startup:**
   - `system_prompt.txt` is read from disk
   - Cached in Python memory (`_SYSTEM_PROMPT_CACHE`)
   - Takes ~1ms

2. **Subsequent assessments:**
   - System prompt retrieved from cache
   - No disk I/O needed
   - Instant access

3. **Shared across sessions:**
   - All concurrent sessions use the same cached prompt
   - Memory efficient
   - Single source of truth

4. **Server restart:**
   - Cache cleared
   - File re-read on next assessment
   - Changes applied

---

## Modifying the Assessment Protocol

### Quick edits (no code changes needed):

1. Open `system_prompt.txt` in any text editor
2. Make your changes
3. Save the file
4. Restart the server
5. Done!

### Example modifications:

- **Add more examples:** Include sample student quotes and ratings
- **Refine rubrics:** Adjust scoring criteria for each domain
- **Add edge cases:** Handle silent students, mixed proficiency, etc.
- **Language-specific patterns:** Add common Korean speaker patterns
- **Expand analogies:** More programming/coding comparisons

### Size guidelines:

| Size | Tokens | Impact | Recommendation |
|------|--------|--------|----------------|
| Current | 1,400 | Perfect | ✅ Optimal |
| 2x (3KB) | 2,800 | Negligible | ✅ Go ahead |
| 5x (7KB) | 7,000 | Minor (+300ms) | ✅ Still good |
| 10x (14KB) | 14,000 | Noticeable (+1s) | ⚠️ Consider chunking |
| 20x+ (28KB+) | 28,000+ | Significant | ❌ Not recommended |

---

## Technical Details

### Caching mechanism:

```python
# In assessment_agent.py
_SYSTEM_PROMPT_CACHE: Optional[str] = None

def _load_system_prompt() -> str:
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        # Read from file (only once)
        with open(prompt_path, 'r', encoding='utf-8') as f:
            _SYSTEM_PROMPT_CACHE = f.read().strip()
    return _SYSTEM_PROMPT_CACHE
```

### When cache is cleared:

- Server restart
- Python process restart
- Manual cache invalidation (not currently implemented)

### To force reload without restart:

Add this function to `assessment_agent.py` if needed:

```python
def reload_system_prompt():
    """Force reload system prompt from file (for hot-reload during dev)"""
    global _SYSTEM_PROMPT_CACHE
    _SYSTEM_PROMPT_CACHE = None
    return _load_system_prompt()
```

---

## Best Practices

✅ **Do:**
- Edit the file directly for protocol changes
- Test changes with sample transcripts
- Keep evidence-based approach
- Use clear, specific language
- Include examples where helpful

❌ **Don't:**
- Make the file unnecessarily long
- Include redundant information
- Use vague or ambiguous criteria
- Forget to restart server after edits
- Remove the core structure sections

---

## Troubleshooting

### Problem: Changes not taking effect

**Solution:** Restart the server. The prompt is cached in memory.

### Problem: Assessment quality declined

**Solution:** Review your edits. Make sure you didn't accidentally remove critical instructions or rubrics.

### Problem: Assessment too slow

**Solution:** Check file size. If > 10KB, consider removing redundant content or using more concise language.

### Problem: File not found error

**Solution:** 
1. Check file exists at `core/resources/system_prompt.txt`
2. Verify file permissions
3. Check working directory

---

## Version History

- **v2.0** (Jan 2026): Consolidated system prompt with pre-loaded protocol (Optimization #1)
- **v1.0** (Original): Split prompt with tool calling for `assess_prot.txt`

---

For questions or issues, refer to `OPTIMIZATIONS_IMPLEMENTED.md` in the web directory.
