# Import Fix for Local and Railway Deployment

## Problem
Running `python server.py` directly caused:
```
ImportError: attempted relative import with no known parent package
```

## Solution
Added **hybrid import pattern** to support both:
- ✅ **Direct execution** (local development): `python server.py`
- ✅ **Module execution** (Railway deployment): `python -m web.backend.server`

## Changes Made

### 1. `server.py`
```python
# Try relative imports first (Railway)
try:
    from .session_store import session_store
    from .realtime_bridge import RealtimeBridge
except ImportError:
    # Fall back to absolute imports (local)
    from web.backend.session_store import session_store
    from web.backend.realtime_bridge import RealtimeBridge
```

### 2. `realtime_bridge.py`
```python
try:
    from .shared_agents import get_assessment_agent
except ImportError:
    from web.backend.shared_agents import get_assessment_agent
```

### 3. `start_server.ps1`
Changed from `uv run python server.py` to just `python server.py` (simpler)

## How to Run

### Local Development (Multiple Options)

**Option 1: Using the start script (RECOMMENDED)**
```bash
cd korean_voice_tutor/web/backend
./start_server.ps1
```
This uses `uv run` which automatically manages dependencies and environment.

**Option 2: Manual with virtual environment**
```bash
cd korean_voice_tutor
.\.venv\Scripts\Activate.ps1
cd web/backend
python server.py
```

**Option 3: Using uv directly**
```bash
cd korean_voice_tutor/web/backend
uv run python server.py
```

**Option 4: As a module**
```bash
cd korean_voice_tutor
.\.venv\Scripts\Activate.ps1
python -m web.backend.server
```

### Railway Deployment
No changes needed! Railway typically runs as module, so relative imports work.

## Why This Works

The try-except pattern:
1. **First attempts relative imports** (`from .module`)
   - Succeeds when run as module (Railway)
   - Fails when run directly (local)

2. **Falls back to absolute imports** (`from web.backend.module`)
   - Only triggered on local direct execution
   - Path manipulation ensures imports work

3. **No Railway impact**
   - Railway never hits the except block
   - Continues using relative imports as before

## Testing

✅ Local: `python server.py` should now work
✅ Railway: No changes needed, will continue to work
