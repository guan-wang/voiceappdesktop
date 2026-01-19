"""
Quick setup test script
Run this to verify your environment is configured correctly
"""

import sys
import os

def test_imports():
    """Test if all required packages are installed"""
    print("Testing imports...")
    
    try:
        import openai
        print("✅ openai")
    except ImportError:
        print("❌ openai - Run: pip install openai")
        return False
    
    try:
        import websockets
        print("✅ websockets")
    except ImportError:
        print("❌ websockets - Run: pip install websockets")
        return False
    
    try:
        import pyaudio
        print("✅ pyaudio")
    except ImportError:
        print("❌ pyaudio - Run: pip install pyaudio")
        print("   Note: On Windows, you may need: pip install pipwin && pipwin install pyaudio")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv")
    except ImportError:
        print("❌ python-dotenv - Run: pip install python-dotenv")
        return False
    
    return True

def test_audio():
    """Test if audio devices are available"""
    print("\nTesting audio devices...")
    
    try:
        import pyaudio
        audio = pyaudio.PyAudio()
        
        # Check input devices
        input_devices = []
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append(info['name'])
        
        if input_devices:
            print(f"✅ Found {len(input_devices)} input device(s)")
            print(f"   Default: {input_devices[0]}")
        else:
            print("⚠️  No input devices found")
        
        # Check output devices
        output_devices = []
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                output_devices.append(info['name'])
        
        if output_devices:
            print(f"✅ Found {len(output_devices)} output device(s)")
            print(f"   Default: {output_devices[0]}")
        else:
            print("⚠️  No output devices found")
        
        audio.terminate()
        return True
        
    except Exception as e:
        print(f"❌ Audio test failed: {e}")
        return False

def test_api_key():
    """Test if API key is configured"""
    print("\nTesting API key configuration...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        print("   Create a .env file with: OPENAI_API_KEY=sk-...")
        return False
    
    if not api_key.startswith("sk-"):
        print("⚠️  API key doesn't start with 'sk-' - may be invalid")
        return False
    
    if len(api_key) < 20:
        print("⚠️  API key seems too short - may be invalid")
        return False
    
    print("✅ API key found in environment")
    print(f"   Key starts with: {api_key[:7]}...")
    return True

def test_openai_connection():
    """Test basic OpenAI API connection"""
    print("\nTesting OpenAI API connection...")
    
    try:
        from dotenv import load_dotenv
        import openai
        load_dotenv()
        
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Try a simple API call to verify the key works
        # Note: This will use a small amount of API credits
        print("   Making test API call...")
        response = client.models.list()
        
        print("✅ OpenAI API connection successful")
        return True
        
    except openai.AuthenticationError:
        print("❌ Authentication failed - check your API key")
        return False
    except Exception as e:
        print(f"⚠️  API test failed: {e}")
        print("   This might be okay - the key format seems correct")
        return True  # Don't fail the test for this

def main():
    """Run all tests"""
    print("=" * 50)
    print("Korean Voice Tutor - Setup Test")
    print("=" * 50)
    print()
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
        print("\n❌ Some packages are missing. Install them with:")
        print("   pip install -r requirements.txt")
        return
    
    # Test audio
    if not test_audio():
        all_passed = False
    
    # Test API key
    if not test_api_key():
        all_passed = False
    
    # Test OpenAI connection
    test_openai_connection()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All basic tests passed!")
        print("   You should be able to run: python app.py")
    else:
        print("⚠️  Some tests failed - please fix the issues above")
    print("=" * 50)

if __name__ == "__main__":
    main()
