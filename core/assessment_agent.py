"""
Assessment Agent - Generates structured proficiency assessment from interview transcript
Uses OpenAI Chat API with function calling and structured outputs
"""

import os
import json
from typing import List
from pydantic import BaseModel
from openai import OpenAI


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
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def get_system_prompt(self) -> str:
        """System prompt for the assessment agent"""
        return """### IDENTITY
You are a Senior ESL Examiner specialized in Semi-Structured Oral Interviews (SSOI). Your goal is to produce a predictable, data-driven proficiency report.

### TASK SEQUENCE
1. CALL `read_guidance()` to load the scoring rubric and WLP Logic.
2. ANALYZE the transcript to locate the "Linguistic Ceiling." (Where did the student stop being comfortable?)
3. GENERATE a structured report based on the evidence found.

### STRICT EVALUATION RULES
- **The "Evidence-First" Rule:** You are forbidden from making a claim without a direct transcript quote.
    - *Bad:* "The student has poor grammar."
    - *Good:* "The student shows a gap in tense consistency (Evidence: 'I go to store yesterday')."
- **The Coding Analogy Rule:** To help the user understand technical linguistic gaps, use coding analogies (C++, Java, or Python).
    - Example: "Using 'stuff' instead of 'infrastructure' is like using a 'Generic Object' type instead of a 'Specific Class'—it lacks the necessary attributes for the task."
- **The Global vs. Local Check:** Prioritize identifying Global Errors that break communication.

### REPORT GENERATION SCHEMA
You must return a report with these specific sections:

#### 1. PROFICIENCY SUMMARY
- **CEFR/ACTFL Level:** [Level]
- **Ceiling Analysis:** Identify which phase (Warm-up, Level-up, or Probe) caused the breakdown.

#### 2. ANALYTIC BREAKDOWN (Table Format)
- **Domain:** [Fluency | Grammar | Lexical | Phonology | Coherence]
- **Rating:** [1-5]
- **Observation:** [Detailed analysis]
- **Evidence:** ["Direct quote from student"]

#### 3. CURRICULUM ROADMAP
- **Starting Point:** Which module should they enter?
- **Logic Errors to Debug:** Top 2 grammatical or lexical patterns to fix.
- **Optimization Strategy:** One specific exercise (e.g., Shadowing, Picture Narration).

### CRITICAL REQUIREMENTS
- ALWAYS call `read_guidance()` first to load the assessment protocol
- ALWAYS provide direct quotes as evidence
- NEVER make claims without supporting evidence from the transcript"""

    def _get_tools(self) -> List[dict]:
        """Define tools available to the assessment agent"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_guidance",
                    "description": "Load the assessment protocol (scoring rubric and WLP Logic) from assess_prot.txt. MUST be called before analysis.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
    
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
        
        Args:
            conversation_history: List of (speaker, text) tuples from the interview
            
        Returns:
            AssessmentReport: Structured report with proficiency analysis
        """
        print("\n📊 Assessment Agent starting analysis...")
        
        # Format the transcript
        transcript = self._format_transcript(conversation_history)
        
        # Create the initial message
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"Please analyze this interview transcript and provide a comprehensive proficiency assessment:\n\n{transcript}"}
        ]
        
        # First API call - agent will call read_guidance() tool
        print("🔧 Calling OpenAI API with function calling enabled...")
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=self._get_tools(),
            tool_choice="auto",
            temperature=0.3,  # Lower for faster, more consistent responses
            max_tokens=2000  # Limit output length for speed
        )
        
        # Handle tool calls (read_guidance)
        while response.choices[0].message.tool_calls:
            print("🔧 Agent is calling tools...")
            
            # Add assistant's response to messages (convert to dict for proper serialization)
            assistant_message = response.choices[0].message
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            # Process each tool call
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                print(f"🔧 Tool called: {function_name}")
                
                if function_name == "read_guidance":
                    # Import and call the read_guidance function
                    from tools.assessment_guidance import read_guidance
                    guidance_text = read_guidance()
                    
                    # Add tool response to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": guidance_text
                    })
                    print(f"✅ Guidance text loaded ({len(guidance_text)} chars)")
            
            # Continue conversation with tool results
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=self._get_tools(),
                tool_choice="auto",
                temperature=0.3,  # Lower for faster, more consistent responses
                max_tokens=2000  # Limit output length for speed
            )
        
        # Now request structured output for the final report
        print("📝 Requesting structured assessment report...")
        final_message = response.choices[0].message
        if final_message.content:
            messages.append({
                "role": "assistant",
                "content": final_message.content
            })
        messages.append({
            "role": "user",
            "content": "Now provide your complete assessment in the structured format."
        })
        
        # Final API call with structured outputs
        structured_response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=AssessmentReport,
            temperature=0.3,  # Lower for faster, more consistent responses
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
