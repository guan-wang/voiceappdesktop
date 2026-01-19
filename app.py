"""
Korean Language Tutor - Main Entry Point
Real-time voice-based Korean language interview with proficiency assessment
"""

import os
import asyncio
from dotenv import load_dotenv
from interview_agent import InterviewAgent
from assessment_generator import AssessmentGenerator

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
    
    # Initialize components
    interview_agent = InterviewAgent()
    assessment_generator = AssessmentGenerator()
    
    try:
        # Run the interview
        await interview_agent.run()
        
    finally:
        # Generate assessment after interview ends
        conversation_history = interview_agent.get_conversation_history()
        
        if conversation_history:
            print("\n" + "=" * 50)
            print("📊 Generating Assessment...")
            print("=" * 50 + "\n")
            
            assessment = assessment_generator.generate_assessment(conversation_history)
            
            print("=" * 50)
            print("📋 ASSESSMENT RESULTS")
            print("=" * 50)
            print(assessment)
            print("=" * 50)

            print("\n" + "=" * 50)
            print("🧾 FULL CONVERSATION HISTORY")
            print("=" * 50)
            for speaker, text in conversation_history:
                print(f"{speaker}: {text}")
            print("=" * 50)
        else:
            print("\n⚠️ No conversation recorded. Assessment skipped.")


if __name__ == "__main__":
    asyncio.run(main())
