"""
Test script for refactored interview agent
Verifies all modules are properly integrated
"""

import asyncio
import sys
import os

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.system('chcp 65001 >nul')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')


def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from audio import AudioManager, CHUNK, FORMAT, CHANNELS, RATE
        print("OK Audio module imports successful")
    except ModuleNotFoundError as e:
        if 'pyaudio' in str(e):
            print("WARN Audio module needs PyAudio (run: pip install -r requirements.txt)")
            print("     Structure is correct, skipping audio test")
        else:
            print(f"FAIL Audio module import failed: {e}")
            return False
    except Exception as e:
        print(f"FAIL Audio module import failed: {e}")
        return False
    
    try:
        from session import SessionManager
        print("OK Session module imports successful")
    except Exception as e:
        print(f"FAIL Session module import failed: {e}")
        return False
    
    try:
        from websocket import EventDispatcher
        print("OK WebSocket module imports successful")
    except Exception as e:
        print(f"FAIL WebSocket module import failed: {e}")
        return False
    
    try:
        from handlers import (
            BaseEventHandler,
            AudioEventHandler,
            TranscriptEventHandler,
            FunctionEventHandler,
            ResponseEventHandler
        )
        print("OK Handlers module imports successful")
    except Exception as e:
        print(f"FAIL Handlers module import failed: {e}")
        return False
    
    try:
        from interview_agent_v2 import InterviewAgent
        print("OK InterviewAgent V2 imports successful")
    except Exception as e:
        print(f"FAIL InterviewAgent V2 import failed: {e}")
        return False
    
    return True


def test_audio_manager():
    """Test AudioManager initialization"""
    print("\nTesting AudioManager...")
    
    try:
        from audio import AudioManager
        audio_mgr = AudioManager()
        print("OK AudioManager created")
        
        # Test cleanup without setup
        audio_mgr.cleanup()
        print("OK AudioManager cleanup works")
        
        return True
    except ModuleNotFoundError as e:
        if 'pyaudio' in str(e):
            print("SKIP AudioManager test (PyAudio not installed)")
            return True  # Not a failure, just not installed yet
        print(f"FAIL AudioManager test failed: {e}")
        return False
    except Exception as e:
        print(f"FAIL AudioManager test failed: {e}")
        return False


def test_session_manager():
    """Test SessionManager"""
    print("\nTesting SessionManager...")
    
    try:
        from session import SessionManager
        session = SessionManager()
        print(f"OK SessionManager created with ID: {session.session_id[:8]}...")
        
        # Test conversation tracking
        session.add_conversation_turn("User", "Hello")
        session.add_conversation_turn("AI", "Hello! Nice to meet you!")
        history = session.get_conversation_history()
        assert len(history) == 2
        print("OK Conversation tracking works")
        
        # Test function tracking
        session.track_function_call("test_function", "test_event")
        assert len(session.function_calls_made) == 1
        print("OK Function tracking works")
        
        return True
    except Exception as e:
        print(f"FAIL SessionManager test failed: {e}")
        return False


def test_event_dispatcher():
    """Test EventDispatcher"""
    print("\nTesting EventDispatcher...")
    
    try:
        from websocket import EventDispatcher
        from session import SessionManager
        from assessment_agent import AssessmentAgent
        from assessment_state_machine import AssessmentStateMachine
        
        # Try to import AudioManager, use None if not available
        try:
            from audio import AudioManager
            audio_manager = AudioManager()
        except ModuleNotFoundError:
            audio_manager = None
            print("     (Using mock AudioManager - PyAudio not installed)")
        
        # Create context
        context = {
            "session": SessionManager(),
            "audio_manager": audio_manager,
            "assessment_agent": AssessmentAgent(),
            "assessment_state": AssessmentStateMachine(),
            "websocket": None  # Mock
        }
        
        dispatcher = EventDispatcher(context)
        print(f"OK EventDispatcher created with {len(dispatcher.handlers)} handlers")
        
        # Test handler registration
        assert len(dispatcher.handlers) == 4
        print("OK Default handlers registered")
        
        return True
    except Exception as e:
        print(f"FAIL EventDispatcher test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_interview_agent():
    """Test InterviewAgent initialization"""
    print("\nTesting InterviewAgent V2...")
    
    try:
        from interview_agent_v2 import InterviewAgent
        agent = InterviewAgent()
        print("OK InterviewAgent V2 created")
        
        # Test configuration methods
        config = agent.get_session_config()
        assert config["type"] == "session.update"
        print("OK Session config generation works")
        
        instructions = agent.get_system_instructions()
        assert "Korean language interviewer" in instructions
        print("OK System instructions generation works")
        
        return True
    except ModuleNotFoundError as e:
        if 'pyaudio' in str(e):
            print("SKIP InterviewAgent V2 test (PyAudio not installed)")
            print("     Note: Install dependencies to fully test")
            return True
        print(f"FAIL InterviewAgent V2 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"FAIL InterviewAgent V2 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("REFACTORED CODE TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("AudioManager Test", test_audio_manager),
        ("SessionManager Test", test_session_manager),
        ("EventDispatcher Test", test_event_dispatcher),
        ("InterviewAgent V2 Test", test_interview_agent)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Results: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\nAll tests passed! Refactored code structure is correct.")
        print("Note: Install dependencies with 'pip install -r requirements.txt' for full testing.")
        return 0
    else:
        print(f"\n{total_count - passed_count} test(s) failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
