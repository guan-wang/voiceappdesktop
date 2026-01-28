# Debugging Assessment Issue

## Current Problem
Assessment tool (`trigger_assessment`) is not being called even when linguistic ceiling is reached.

## Symptoms from Logs
```
🔧 [4251bdd5] Function call:    <- Empty function name!
```

This means:
1. OpenAI IS sending a function call event
2. But we're NOT extracting the function name correctly
3. So the tool never executes

## Root Cause Hypotheses

### 1. Event Structure Mismatch
The event structure from OpenAI might be different than expected.

**What we're checking:**
- `event.get("function_call", {}).get("name")`
- `event.get("item", {}).get("name")`

**What it might actually be:**
- Different nesting level
- Different key names
- Split across multiple events

### 2. Wrong Event Type
We're listening for: `response.function_call_arguments.done`

**OpenAI might send:**
- `response.output_item.done` (with item.type == "function_call")
- `response.function_call.completed`
- Some other event type

### 3. Tool Not Registered Properly
OpenAI might not be recognizing the tool definition.

**Possible issues:**
- Tool definition format incorrect
- `tool_choice: "auto"` not working
- Model doesn't support tools in Realtime API

## Fixes Applied

### 1. Comprehensive Event Logging ✅
Added logging to see EVERY event from OpenAI:

```python
# Log all tool/function events with FULL details
if "function" in event_type.lower() or "tool" in event_type.lower():
    print(f"🔔🔔🔔 *** TOOL/FUNCTION EVENT: {event_type} ***")
    print(json.dumps(event, indent=2))
```

**This will show us the actual event structure!**

### 2. Multiple Event Type Handlers ✅
Now listening for multiple possible event types:

```python
elif event_type == "response.function_call_arguments.done":
    await self.handle_function_call(event)

elif event_type == "response.output_item.done":
    item = event.get("item", {})
    if item.get("type") == "function_call":
        await self.handle_function_call(event)
```

### 3. Robust Function Name Extraction ✅
Try multiple possible locations:

```python
function_name = (
    function_call.get("name", "") or
    item.get("name", "") or
    event.get("name", "")
)
```

### 4. Tool Registration Logging ✅
Show which tools are being sent to OpenAI:

```python
print(f"🔧 Registering {len(tools)} tools:")
for tool in tools:
    print(f"   📎 {tool['name']}: {tool['description'][:60]}...")
```

## Testing Instructions

### Step 1: Restart Server
```powershell
cd web\backend
.\stop_server.ps1
.\start_server.ps1
```

### Step 2: Watch for Tool Registration
You should see:
```
🔧 [session] Registering 2 tools with OpenAI:
   📎 interview_guidance: CRITICAL: Load the interview guidance protocol...
   📎 trigger_assessment: MANDATORY: Call when user reached linguistic...
```

### Step 3: Start Interview
When interview starts, you should see:
```
📨 [session] Event: session.created
📨 [session] Event: session.updated
📨 [session] Event: response.created
📨 [session] Event: response.output_item.added
🔔🔔🔔 *** TOOL/FUNCTION EVENT: response.output_item.done ***
{
  "type": "response.output_item.done",
  "item": {
    "type": "function_call",
    "name": "interview_guidance",
    ...
  }
}
```

### Step 4: Reach Ceiling
Have conversation until AI detects ceiling. Watch for:
```
🔔🔔🔔 *** TOOL/FUNCTION EVENT: ??? ***
{
  ... actual event structure will be shown ...
}
```

**THIS IS THE KEY!** The full event JSON will tell us:
1. What event type OpenAI actually sends
2. Where the function name is located
3. What the structure looks like

### Step 5: Analyze
Based on what we see, we'll know:

**If no tool event appears:**
→ AI is not calling the tool at all (instruction problem)

**If tool event appears but function name is wrong/missing:**
→ Parsing problem (need to fix extraction logic)

**If tool event appears with correct name but no execution:**
→ Call ID problem or handler not reached

## Alternative Approaches if This Fails

### Option A: Force Tool Call on Specific Keyword
If AI won't call tool automatically, detect keywords:

```python
if "ceiling" in ai_text.lower() or "assessment" in ai_text.lower():
    # Manually trigger assessment
    await self._generate_and_deliver_assessment()
```

### Option B: Conversation Turn Limit
After N turns, automatically trigger:

```python
if len(self.session.conversation_history) >= 20:
    print("Auto-triggering assessment after 20 turns")
    await self._generate_and_deliver_assessment()
```

### Option C: Client-Side Trigger
Add "End Interview" button:

```javascript
<button onclick="endInterview()">End & Get Assessment</button>
```

## Expected Output from Next Test

When you run the interview again, the terminal will show:

1. **Tool registration** (at startup)
2. **All OpenAI events** (during conversation)
3. **Full JSON of tool events** (when tools are called)

**Copy the terminal output and share it!** The JSON will tell us exactly what's wrong.

## Quick Reference

### What to Look For

✅ **Tools registered:**
```
🔧 Registering 2 tools with OpenAI:
   📎 interview_guidance
   📎 trigger_assessment
```

✅ **Initial tool call (interview_guidance):**
```
🔔🔔🔔 *** TOOL/FUNCTION EVENT: response.output_item.done ***
```

❓ **Ceiling tool call (trigger_assessment):**
```
🔔🔔🔔 *** TOOL/FUNCTION EVENT: ??? ***
```
**↑ THIS IS WHAT WE NEED TO SEE!**

### Commands

```powershell
# Stop server
cd web\backend
.\stop_server.ps1

# Start with fresh logs
.\start_server.ps1

# Server will run - watch terminal output carefully
# Do a full interview
# Save/copy terminal output after
```

## Next Steps

1. Run test interview
2. Copy terminal logs (especially tool events)
3. Share logs
4. We'll see the actual event structure
5. Fix the parsing based on reality
6. Assessment will work! 🎉
