"""
Quick test to verify UV setup and dependencies
Run with: uv run python test_uv_setup.py
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

def test_imports():
    """Test that all core dependencies can be imported"""
    print("🧪 Testing UV Setup...\n")
    
    tests = []
    
    # Core dependencies
    try:
        import openai
        print(f"✅ openai: {openai.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"❌ openai: {e}")
        tests.append(False)
    
    try:
        import pydantic
        print(f"✅ pydantic: {pydantic.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"❌ pydantic: {e}")
        tests.append(False)
    
    try:
        import websockets
        print(f"✅ websockets: {websockets.__version__}")
        tests.append(True)
    except ImportError as e:
        print(f"❌ websockets: {e}")
        tests.append(False)
    
    try:
        from dotenv import load_dotenv
        print(f"✅ python-dotenv: installed")
        tests.append(True)
    except ImportError as e:
        print(f"❌ python-dotenv: {e}")
        tests.append(False)
    
    # Desktop-specific (optional)
    try:
        import pyaudio
        print(f"✅ pyaudio: installed (desktop available)")
        tests.append(True)
    except ImportError:
        print(f"⚠️  pyaudio: not installed (desktop not available, web-only setup)")
        # Don't fail test - pyaudio is optional for web
    
    # Web-specific (optional)
    try:
        import fastapi
        print(f"✅ fastapi: {fastapi.__version__} (web available)")
        tests.append(True)
    except ImportError:
        print(f"⚠️  fastapi: not installed (web not available, desktop-only setup)")
        # Don't fail test - fastapi is optional for desktop
    
    try:
        import uvicorn
        print(f"✅ uvicorn: {uvicorn.__version__} (web available)")
        tests.append(True)
    except ImportError:
        print(f"⚠️  uvicorn: not installed (web not available, desktop-only setup)")
        # Don't fail test - uvicorn is optional for desktop
    
    print()
    
    # Summary
    passed = sum(tests)
    total = len(tests)
    
    print("=" * 50)
    print(f"Core Dependencies: {passed}/{total} passed")
    
    if passed == total:
        print("\n✅ All core dependencies installed!")
        print("\n📝 Next steps:")
        print("   - Desktop: cd desktop && uv run python app_v2.py")
        print("   - Web: cd web/backend && uv run python server.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} core dependencies missing")
        print("\n📝 Fix with: uv sync")
        return 1

def test_core_modules():
    """Test that core modules can be imported"""
    print("\n🧪 Testing Core Modules...\n")
    
    # Add paths
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    tests = []
    
    try:
        from core import AssessmentAgent
        print("✅ core.AssessmentAgent imported")
        tests.append(True)
    except ImportError as e:
        print(f"❌ core.AssessmentAgent: {e}")
        tests.append(False)
    
    try:
        from core import AssessmentStateMachine
        print("✅ core.AssessmentStateMachine imported")
        tests.append(True)
    except ImportError as e:
        print(f"❌ core.AssessmentStateMachine: {e}")
        tests.append(False)
    
    try:
        from core.tools.interview_guidance import get_interview_guidance
        print("✅ core.tools.interview_guidance imported")
        tests.append(True)
    except ImportError as e:
        print(f"❌ core.tools.interview_guidance: {e}")
        tests.append(False)
    
    print()
    
    passed = sum(tests)
    total = len(tests)
    
    print("=" * 50)
    print(f"Core Modules: {passed}/{total} passed")
    
    if passed == total:
        print("\n✅ All core modules working!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} core modules failed")
        print("   Check that core/ directory is properly set up")
        return 1

def test_env():
    """Test environment configuration"""
    print("\n🧪 Testing Environment...\n")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key:
        print(f"✅ OPENAI_API_KEY configured (starts with: {api_key[:7]}...)")
        print("\n✅ Environment ready!")
        return 0
    else:
        print("⚠️  OPENAI_API_KEY not found in environment")
        print("\n📝 Create .env file with:")
        print("   OPENAI_API_KEY=sk-your-key-here")
        return 1

def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("UV SETUP TEST")
    print("=" * 50 + "\n")
    
    print(f"Python: {sys.version}")
    print(f"Path: {sys.executable}\n")
    
    # Run tests
    results = []
    
    results.append(test_imports())
    results.append(test_core_modules())
    results.append(test_env())
    
    # Final summary
    print("\n" + "=" * 50)
    print("FINAL SUMMARY")
    print("=" * 50)
    
    if all(r == 0 for r in results):
        print("\n🎉 Everything is set up correctly!")
        print("\nYou're ready to run:")
        print("  Desktop: uv run python desktop/app_v2.py")
        print("  Web: uv run python web/backend/server.py")
        return 0
    else:
        print("\n⚠️  Some issues found. Run: uv sync")
        return 1

if __name__ == "__main__":
    exit(main())
