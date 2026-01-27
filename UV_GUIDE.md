# Using UV with Korean Voice Tutor

This project is configured to work with `uv` - the fast Python package manager.

## Quick Start with UV

### Option 1: Install Everything (Desktop + Web)

```bash
# From project root
uv sync
```

This installs all dependencies for both desktop and web versions.

### Option 2: Install Desktop Only

```bash
cd desktop
uv sync
```

### Option 3: Install Web Only

```bash
cd web/backend
uv sync
```

### Option 4: Install Core Only

```bash
cd core
uv sync
```

## Running with UV

### Desktop Version

```bash
cd desktop
uv run python app_v2.py
```

### Web Version

```bash
cd web/backend
uv run python server.py
```

## Installing UV

If you don't have `uv` yet:

```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# Mac/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

## Project Structure with UV

```
korean_voice_tutor/
├── pyproject.toml          # 🏠 Root workspace
│   └── [tool.uv.workspace] # Manages all subprojects
│
├── core/
│   └── pyproject.toml      # Core dependencies
│
├── desktop/
│   └── pyproject.toml      # Desktop dependencies
│
└── web/backend/
    └── pyproject.toml      # Web dependencies
```

## UV Commands

### Sync Dependencies

```bash
# Sync all workspaces
uv sync

# Sync specific workspace
cd desktop && uv sync

# Sync with dev dependencies
uv sync --extra dev
```

### Add New Package

```bash
# Add to root
uv add fastapi

# Add to specific workspace
cd desktop && uv add pyaudio

# Add dev dependency
uv add --dev pytest
```

### Remove Package

```bash
uv remove package-name
```

### Update Dependencies

```bash
# Update all
uv sync --upgrade

# Update specific package
uv sync --upgrade-package openai
```

### Run Commands

```bash
# Run Python script
uv run python script.py

# Run with specific Python version
uv run --python 3.11 python script.py
```

### Create Virtual Environment

```bash
# UV creates .venv automatically when you run uv sync
# But you can also create manually:
uv venv

# Activate it (optional, uv run handles this)
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

## Optional Dependencies

The root `pyproject.toml` includes optional dependency groups:

```bash
# Install only desktop dependencies
uv sync --extra desktop

# Install only web dependencies
uv sync --extra web

# Install dev dependencies
uv sync --extra dev

# Install multiple groups
uv sync --extra desktop --extra dev
```

## Workspace Features

UV's workspace feature allows you to:

1. **Manage all subprojects together:**
   ```bash
   # From root, sync everything
   uv sync
   ```

2. **Share common dependencies:**
   - Core packages defined once
   - Used by all subprojects

3. **Independent development:**
   ```bash
   # Work on just web
   cd web/backend && uv sync
   ```

## Migration from pip/requirements.txt

If you were using `requirements.txt`:

```bash
# Old way
pip install -r requirements.txt

# New way with uv
uv sync

# Or directly run without syncing first
uv run python app.py
```

UV automatically:
- Creates virtual environment
- Installs dependencies
- Much faster than pip

## Troubleshooting

### Issue: "uv: command not found"

```bash
# Install uv first
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or on Windows
irm https://astral.sh/uv/install.ps1 | iex
```

### Issue: PyAudio won't install (Windows)

```bash
# PyAudio can be tricky on Windows
# If uv sync fails, try:
uv pip install pipwin
uv run pipwin install pyaudio
```

Or download wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

### Issue: Dependencies conflict

```bash
# Clear cache and reinstall
uv cache clean
uv sync --refresh
```

## UV vs Pip Performance

Example install times (Desktop dependencies):

```
pip:  ~45 seconds
uv:   ~3 seconds  ⚡ 15x faster!
```

## Best Practices

### 1. Always use `uv sync` after pulling changes

```bash
git pull
uv sync
```

### 2. Lock dependencies with uv.lock

```bash
# UV automatically creates uv.lock
# Commit this file to git for reproducibility
git add uv.lock
git commit -m "Lock dependencies"
```

### 3. Use workspace for shared dependencies

Already configured! Just run `uv sync` from root.

### 4. Keep pyproject.toml clean

```toml
# Good: version ranges
dependencies = [
    "openai>=1.102.0",
]

# Avoid: exact pins (unless required)
dependencies = [
    "openai==1.102.0",
]
```

## Quick Reference

| Task | Command |
|------|---------|
| Install all deps | `uv sync` |
| Install desktop only | `cd desktop && uv sync` |
| Install web only | `cd web/backend && uv sync` |
| Run desktop app | `uv run python desktop/app_v2.py` |
| Run web server | `uv run python web/backend/server.py` |
| Add package | `uv add package-name` |
| Remove package | `uv remove package-name` |
| Update all | `uv sync --upgrade` |
| Clean cache | `uv cache clean` |

## Testing with UV

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Run specific test
uv run pytest tests/test_audio.py
```

## IDE Integration

### VS Code

1. UV creates `.venv` automatically
2. VS Code should detect it
3. If not, select interpreter:
   - Ctrl+Shift+P
   - "Python: Select Interpreter"
   - Choose `.venv/Scripts/python.exe`

### PyCharm

1. Settings → Project → Python Interpreter
2. Add → Existing Environment
3. Select `.venv/Scripts/python.exe`

## Resources

- UV Docs: https://docs.astral.sh/uv/
- GitHub: https://github.com/astral-sh/uv
- Discord: https://discord.gg/astral-sh

## Summary

UV makes dependency management **fast and simple**:

✅ **15x faster** than pip
✅ **Automatic** virtual environments
✅ **Workspace** support for monorepos
✅ **Compatible** with pyproject.toml
✅ **Drop-in** replacement for pip

Just run `uv sync` and you're ready to go! 🚀
