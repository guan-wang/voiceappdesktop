"""
Korean Language Tutor - Main Entry Point with Version Switch
Easily switch between original and refactored versions
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===== VERSION SWITCH =====
# Set to 'v1' for original, 'v2' for refactored
USE_VERSION = 'v2'
# ==========================

if USE_VERSION == 'v2':
    from interview_agent_v2 import InterviewAgent
    print("🔄 Using refactored version (V2)")
else:
    from interview_agent import InterviewAgent
    print("🔄 Using original version (V1)")


async def main():
    """Main entry point"""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("   Please create a .env file with your OpenAI API key")
        print("   Example: OPENAI_API_KEY=sk-...")
        return
    
    # Initialize interview agent
    interview_agent = InterviewAgent()
    
    try:
        # Run the interview
        await interview_agent.run()
        
    finally:
        # Print conversation history
        if USE_VERSION == 'v2':
            conversation_history = interview_agent.session.get_conversation_history()
        else:
            conversation_history = interview_agent.get_conversation_history()
        
        if conversation_history:
            print("\n" + "=" * 50)
            print("🧾 CONVERSATION HISTORY")
            print("=" * 50)
            for speaker, text in conversation_history:
                print(f"{speaker}: {text}")
            print("=" * 50)
            print("\n💡 Assessment report has been saved to the reports/ directory")
        else:
            print("\n⚠️ No conversation recorded.")


if __name__ == "__main__":
    asyncio.run(main())
