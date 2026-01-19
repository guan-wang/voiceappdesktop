"""
Korean Language Tutor - Sync (Push-to-Talk) Entry Point
Synchronous turn-taking with async upload and streaming AI output.
"""

import os
import asyncio
from dotenv import load_dotenv
from interview_agent_synch import InterviewAgentSynch


load_dotenv()


async def main():
    """Main entry point."""
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("   Please create a .env file with your OpenAI API key")
        print("   Example: OPENAI_API_KEY=sk-...")
        return

    interview_agent = InterviewAgentSynch()
    await interview_agent.run()


if __name__ == "__main__":
    asyncio.run(main())
