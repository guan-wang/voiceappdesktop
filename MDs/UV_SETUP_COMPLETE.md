# ✅ UV Setup Complete!

Your Korean Voice Tutor is now fully configured to work with **UV** - the fast Python package manager!

## What Was Added

### 1. **pyproject.toml Files**
```
├── pyproject.toml              # Root workspace (manages everything)
├── core/pyproject.toml         # Core dependencies
├── desktop/pyproject.toml      # Desktop dependencies  
└── web/backend/pyproject.toml  # Web dependencies
```

### 2. **UV Workspace**
The root `pyproject.toml` includes a workspace configuration that manages all subprojects together!

### 3. **Documentation**
- `UV_GUIDE.md` - Complete UV usage guide
- `test_uv_setup.py` - Verify everything works

## Quick Start with UV

### 1. Install UV (if you haven't)
```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# Already installed? Skip this!
```

### 2. Sync Dependencies
```bash
# From project root - installs everything
uv sync

# Or install only what you need:
cd desktop && uv sync     # Desktop only
cd web/backend && uv sync # Web only
```

### 3. Test Setup
```bash
uv run python test_uv_setup.py
```

You should see:
```
✅ openai: x.x.x
✅ pydantic: x.x.x  
✅ websockets: x.x.x
✅ All core dependencies installed!
```

### 4. Run Your App

**Desktop:**
```bash
cd desktop
uv run python app_v2.py
```

**Web:**
```bash
cd web/backend
uv run python server.py
```

## Why UV?

- ⚡ **15x faster** than pip
- 🔒 **Better dependency resolution**
- 🏗️ **Workspace support** (monorepo)
- 🤝 **Drop-in pip replacement**

## UV vs Pip Comparison

| Task | Pip | UV |
|------|-----|-----|
| Install deps | `pip install -r requirements.txt` | `uv sync` |
| Add package | `pip install package` | `uv add package` |
| Run script | `python script.py` | `uv run python script.py` |
| Create venv | `python -m venv .venv` | `uv venv` (auto) |
| Time | ~45s | ~3s ⚡ |

## Common Commands

```bash
# Install all dependencies
uv sync

# Install with dev dependencies
uv sync --extra dev

# Add new package
uv add fastapi

# Remove package
uv remove fastapi

# Update all packages
uv sync --upgrade

# Run Python script
uv run python script.py

# Run tests
uv run pytest
```

## Workspace Benefits

With the workspace setup, you can:

1. **Manage everything from root:**
   ```bash
   cd korean_voice_tutor
   uv sync  # Installs core, desktop, and web!
   ```

2. **Or work independently:**
   ```bash
   cd desktop && uv sync    # Just desktop
   cd web/backend && uv sync # Just web
   ```

3. **Shared dependencies automatically handled:**
   - Core packages installed once
   - Used by all subprojects
   - No duplication!

## File Structure

```
korean_voice_tutor/
├── pyproject.toml          # 🏠 Workspace root
│   ├── dependencies = [...]    # All packages
│   └── [tool.uv.workspace]     # Links subprojects
│
├── uv.lock                 # 🔒 Dependency lock file
│   └── Auto-generated, commit to git!
│
├── .venv/                  # 🐍 Virtual environment
│   └── Auto-created by uv sync
│
├── core/
│   └── pyproject.toml      # Core-specific deps
│
├── desktop/
│   └── pyproject.toml      # Desktop-specific deps
│
└── web/backend/
    └── pyproject.toml      # Web-specific deps
```

## Next Steps

1. **Run test:**
   ```bash
   uv run python test_uv_setup.py
   ```

2. **Try desktop:**
   ```bash
   cd desktop
   uv run python app_v2.py
   ```

3. **Try web:**
   ```bash
   cd web/backend
   uv run python server.py
   ```

4. **Read full guide:**
   ```bash
   cat UV_GUIDE.md
   ```

## Troubleshooting

### "uv: command not found"
Install UV first:
```bash
irm https://astral.sh/uv/install.ps1 | iex
```

### Dependencies not installing
```bash
uv cache clean
uv sync --refresh
```

### PyAudio fails (Windows)
PyAudio can be tricky on Windows. If it fails:
```bash
# Skip PyAudio for now, use web version
cd web/backend && uv sync
```

Or download wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

## Documentation

- `UV_GUIDE.md` - Complete UV documentation
- `QUICK_START.md` - Updated with UV instructions
- `test_uv_setup.py` - Verify your setup

## Summary

✅ **pyproject.toml** files created for all subprojects
✅ **UV workspace** configured  
✅ **Dependencies** defined
✅ **Test script** ready
✅ **Documentation** complete

**Just run:** `uv sync` and you're ready! 🚀

---

**UV is now your default package manager for this project!**

Old way (still works):
```bash
pip install -r requirements.txt
python app.py
```

New way (faster):
```bash
uv sync
uv run python app.py
```

Enjoy the speed boost! ⚡
