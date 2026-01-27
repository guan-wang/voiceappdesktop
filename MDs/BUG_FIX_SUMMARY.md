# Bug Fix Summary - Assessment Agent Tool Definition

## The Problem

After the interview agent detected the linguistic ceiling and triggered assessment, the system failed with this error:

```
❌ Event handler error: Error code: 400 - {'error': {'message': "Missing required parameter: 'tools[0].function'.", 'type': 'invalid_request_error', 'param': 'tools[0].function', 'code': 'missing_required_parameter'}}
```

## Root Cause

The `assessment_agent.py` was using the **Realtime API** tool definition format instead of the **Chat API** format.

### Wrong Format (Realtime API - Flat Structure):
```python
{
    "type": "function",
    "name": "read_guidance",              # ❌ WRONG for Chat API
    "description": "...",
    "parameters": {...}
}
```

### Correct Format (Chat API - Nested Structure):
```python
{
    "type": "function",
    "function": {                          # ✅ CORRECT - nested under "function"
        "name": "read_guidance",
        "description": "...",
        "parameters": {...}
    }
}
```

## The Fix

### 1. Fixed Tool Definition (Lines 83-99)

**Before:**
```python
def _get_tools(self) -> List[dict]:
    return [
        {
            "type": "function",
            "name": "read_guidance",
            "description": "Load the assessment protocol...",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    ]
```

**After:**
```python
def _get_tools(self) -> List[dict]:
    return [
        {
            "type": "function",
            "function": {                      # ← Added nested "function" key
                "name": "read_guidance",
                "description": "Load the assessment protocol...",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []             # ← Added required array
                }
            }
        }
    ]
```

### 2. Improved Message Serialization (Lines 141-161)

**Before:**
```python
# Add assistant's response to messages
messages.append(response.choices[0].message)
```

**After:**
```python
# Add assistant's response to messages (convert to dict for proper serialization)
assistant_message = response.choices[0].message
messages.append({
    "role": "assistant",
    "content": assistant_message.content,
    "tool_calls": [
        {
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.function.name,
                "arguments": tc.function.arguments
            }
        }
        for tc in assistant_message.tool_calls
    ]
})
```

### 3. Fixed Final Message Append (Lines 191-196)

**Before:**
```python
messages.append(response.choices[0].message)
```

**After:**
```python
final_message = response.choices[0].message
if final_message.content:
    messages.append({
        "role": "assistant",
        "content": final_message.content
    })
```

## Why This Happened

The interview agent uses the **Realtime API** (WebSocket-based voice API) which has a different tool definition format than the **Chat API** (REST-based text API).

| API | Tool Format | Used By |
|-----|-------------|---------|
| **Realtime API** | Flat structure (`name` at top level) | `interview_agent.py` |
| **Chat API** | Nested structure (`function` key) | `assessment_agent.py` |

The assessment agent was incorrectly copied from the Realtime API format.

## Testing

The fix should now allow:
1. ✅ Interview agent triggers assessment at linguistic ceiling
2. ✅ Assessment agent calls `read_guidance()` tool successfully
3. ✅ Assessment protocol is loaded from `assess_prot.txt`
4. ✅ Structured report is generated using Pydantic models
5. ✅ Verbal summary is spoken to user
6. ✅ Report is saved to `reports/` directory
7. ✅ Session ends gracefully

## Next Steps

Run the interview again:
```bash
cd korean_voice_tutor
uv run app.py
```

The assessment should now complete successfully without errors.
