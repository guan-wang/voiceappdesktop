# How to Run - Entry Points

You have multiple ways to run the Korean Voice Tutor. Choose based on your preference:

## Option 1: Direct Execution (Simplest)

Run the agent directly without a separate app.py:

### Original Version
```bash
python interview_agent.py
```

### Refactored Version (V2)
```bash
python interview_agent_v2.py
```

**Pros:** Simple, one command
**Cons:** No API key checking, no conversation history printout at end

---

## Option 2: Using app.py (Original)

Use the original app.py with nice features:

```bash
python app.py
```

**Features:**
- ✅ API key validation
- ✅ Environment variable loading (.env)
- ✅ Conversation history printout at end
- ✅ Error handling

**Uses:** `interview_agent.py` (original version)

---

## Option 3: Using app_v2.py (Refactored)

Use the new app with refactored agent:

```bash
python app_v2.py
```

**Features:**
- ✅ API key validation
- ✅ Environment variable loading (.env)
- ✅ Conversation history printout at end
- ✅ Error handling

**Uses:** `interview_agent_v2.py` (refactored version)

---

## Option 4: Using app_switch.py (Best for Testing)

Use the version-switchable app:

```bash
python app_switch.py
```

**Features:**
- ✅ All features from app.py
- ✅ Easy version switching via config
- ✅ Compare both versions side-by-side

To switch versions, edit line 12 in `app_switch.py`:
```python
USE_VERSION = 'v2'  # or 'v1' for original
```

---

## Recommendation

**For production:** Use `app_v2.py` with refactored code

**For testing:** Use `app_switch.py` to easily compare versions

**For quick tests:** Run `python interview_agent_v2.py` directly

---

## What's the Difference?

| Entry Point | Version | Features | Best For |
|------------|---------|----------|----------|
| `interview_agent.py` | V1 | Basic | Quick test of original |
| `interview_agent_v2.py` | V2 | Basic | Quick test of refactored |
| `app.py` | V1 | Full | Production (original) |
| `app_v2.py` | V2 | Full | Production (refactored) |
| `app_switch.py` | Both | Full + Switch | Testing & Comparison |

---

## Quick Start

**First time?** Use this:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file with your API key
echo OPENAI_API_KEY=sk-your-key-here > .env

# 3. Run the refactored version
python app_v2.py
```

**Already working?** Just switch:

```bash
# Change from:
python app.py

# To:
python app_v2.py
```

That's it! Same functionality, cleaner code.
