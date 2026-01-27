"""
Korean Language Tutor - Main Entry Point (V2)
Real-time voice-based Korean language interview with proficiency assessment
Using refactored modular architecture
"""

import os
import asyncio
from dotenv import load_dotenv
from interview_agent_v2 import InterviewAgent

# Load environment variables
load_dotenv()


async def main():
    """Main entry point"""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("   Please create a .env file with your OpenAI API key")
        print("   Example: OPENAI_API_KEY=sk-...")
        return
    
    # Initialize interview agent (includes integrated assessment agent)
    interview_agent = InterviewAgent()
    
    try:
        # Run the interview with integrated assessment
        # Assessment is triggered automatically when linguistic ceiling is reached
        await interview_agent.run()
        
    finally:
        # Optional: Print conversation history for debugging/logging
        conversation_history = interview_agent.session.get_conversation_history()
        
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
