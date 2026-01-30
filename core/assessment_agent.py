"""
Assessment Agent - Generates structured proficiency assessment from interview transcript
Uses OpenAI Chat API with structured outputs (optimized for speed)
"""

import os
import json
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI


# Module-level cache for system prompt (loaded once per process)
_SYSTEM_PROMPT_CACHE: Optional[str] = None


def _load_system_prompt() -> str:
    """Load system prompt from file and cache it in memory"""
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        module_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(module_dir, "resources", "system_prompt.txt")
        prompt_path = os.path.normpath(prompt_path)
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            _SYSTEM_PROMPT_CACHE = f.read().strip()
        
        print(f"📋 System prompt loaded ({len(_SYSTEM_PROMPT_CACHE)} chars)")
    
    return _SYSTEM_PROMPT_CACHE


class DomainAnalysis(BaseModel):
    """Analysis of a specific linguistic domain"""
    domain: str  # Fluency | Grammar | Lexical | Phonology | Coherence
    rating: int  # 1-5 scale
    observation: str  # Detailed analysis
    evidence: str  # Direct quote from student transcript


class AssessmentReport(BaseModel):
    """Structured assessment report following SSOI specification"""
    proficiency_level: str  # CEFR/ACTFL Level
    ceiling_phase: str  # Warm-up, Level-up, or Probe
    ceiling_analysis: str  # Detailed explanation of where breakdown occurred
    domain_analyses: List[DomainAnalysis]  # Analytic breakdown across 5 domains
    starting_module: str  # Which curriculum module should they enter
    logic_errors_to_debug: List[str]  # Top 2 grammatical or lexical patterns to fix
    optimization_strategy: str  # One specific exercise (e.g., Shadowing, Picture Narration)


class AssessmentAgent:
    """
    Senior ESL Examiner agent that produces predictive, data-driven proficiency reports.
    Uses Semi-Structured Oral Interview (SSOI) methodology.
    
    Optimized for speed with pre-loaded system prompt (no tool calling).
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Pre-load system prompt on initialization
        self.system_prompt = _load_system_prompt()
        
    def get_system_prompt(self) -> str:
        """Get the cached system prompt"""
        return self.system_prompt
    
    def _format_transcript(self, conversation_history: List[tuple]) -> str:
        """Format conversation history into a readable transcript"""
        transcript_lines = []
        transcript_lines.append("=== INTERVIEW TRANSCRIPT ===\n")
        
        for speaker, text in conversation_history:
            transcript_lines.append(f"{speaker}: {text}")
        
        transcript_lines.append("\n=== END TRANSCRIPT ===")
        return "\n".join(transcript_lines)
    
    def generate_assessment(self, conversation_history: List[tuple]) -> AssessmentReport:
        """
        Generate structured assessment report from interview transcript.
        
        Optimized version with single API call - no tool calling needed.
        System prompt already includes assessment protocol.
        
        Args:
            conversation_history: List of (speaker, text) tuples from the interview
            
        Returns:
            AssessmentReport: Structured report with proficiency analysis
        """
        print("\n📊 Assessment Agent starting analysis...")
        
        # Format the transcript
        transcript = self._format_transcript(conversation_history)
        
        # Create messages with pre-loaded system prompt
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"Please analyze this interview transcript and provide a comprehensive proficiency assessment:\n\n{transcript}"}
        ]
        
        # Single API call with structured output - faster than tool calling!
        print("🚀 Calling OpenAI API with structured output...")
        structured_response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=AssessmentReport,
            temperature=0.1,  # Very low for fast, deterministic assessment
            max_tokens=1500  # Structured output, limit for speed
        )
        
        report = structured_response.choices[0].message.parsed
        print("✅ Assessment report generated successfully")
        
        return report
    
    def report_to_verbal_summary(self, report: AssessmentReport) -> str:
        """
        Convert structured report into a friendly verbal summary for the interview agent to speak.
        This will be read aloud to the user.
        
        Args:
            report: The structured AssessmentReport
            
        Returns:
            str: A conversational summary suitable for text-to-speech
        """
        summary_parts = []
        
        # Opening
        summary_parts.append(f"Based on our conversation, I've assessed your Korean proficiency at {report.proficiency_level} level.")
        
        # Ceiling analysis
        summary_parts.append(f"You performed well during the {report.ceiling_phase} phase. {report.ceiling_analysis}")
        
        # Highlight strengths and areas for improvement
        summary_parts.append("\nLet me break down the key areas:")
        
        # Find strongest and weakest domains
        sorted_domains = sorted(report.domain_analyses, key=lambda x: x.rating, reverse=True)
        strongest = sorted_domains[0]
        weakest = sorted_domains[-1]
        
        summary_parts.append(f"Your strongest area is {strongest.domain.lower()} with a rating of {strongest.rating} out of 5. {strongest.observation}")
        summary_parts.append(f"An area to focus on is {weakest.domain.lower()}, rated at {weakest.rating} out of 5. {weakest.observation}")
        
        # Learning recommendations
        summary_parts.append(f"\nI recommend starting with the {report.starting_module} module.")
        summary_parts.append("The top patterns to work on are:")
        for i, error in enumerate(report.logic_errors_to_debug, 1):
            summary_parts.append(f"{i}. {error}")
        
        summary_parts.append(f"\nFor practice, I suggest this exercise: {report.optimization_strategy}")
        
        # Closing
        summary_parts.append("\nYou're making good progress! Keep practicing regularly.")
        
        return " ".join(summary_parts)
