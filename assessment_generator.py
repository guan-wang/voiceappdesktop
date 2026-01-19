"""
Assessment Generator - MVP implementation for Korean language proficiency assessment
Generates CEFR level predictions based on conversation history
"""

import os
from openai import OpenAI
from typing import List, Tuple


class AssessmentGenerator:
    """Generates Korean language proficiency assessments from conversation history"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def format_conversation(self, conversation_history: List[Tuple[str, str]]) -> str:
        """Format conversation history into readable text"""
        if not conversation_history:
            return "No conversation recorded."
        
        formatted_lines = []
        for speaker, text in conversation_history:
            speaker_label = "Interviewer" if speaker == "AI" else "Learner"
            formatted_lines.append(f"{speaker_label}: {text}")
        
        return "\n".join(formatted_lines)
    
    def get_assessment_prompt(self, conversation_text: str) -> str:
        """Generate the assessment prompt"""
        return f"""You are a Korean language assessment expert. Based on the following conversation between an interviewer and a Korean learner, provide a comprehensive assessment.

Analyze the conversation and provide:

1. **Predicted CEFR Level**: Choose one level (A1, A2, B1, B2, C1, or C2)
2. **Explanation**: 2-3 sentences explaining why this level was assigned, based on the tasks attempted and their success/failure
3. **Strengths**: One specific strength demonstrated by the learner (e.g., vocabulary range, grammar accuracy, fluency, communication effectiveness)
4. **Weaknesses**: One specific area that needs improvement (e.g., grammar errors, limited vocabulary, pronunciation, sentence complexity)

Be specific and reference examples from the conversation when possible.

Conversation:
{conversation_text}

Assessment:"""
    
    def generate_assessment(self, conversation_history: List[Tuple[str, str]]) -> str:
        """
        Generate assessment based on conversation history
        
        Args:
            conversation_history: List of (speaker, text) tuples where speaker is "AI" or "User"
        
        Returns:
            Assessment text string
        """
        if not conversation_history:
            return "⚠️ No conversation data available for assessment."
        
        try:
            # Format conversation
            conversation_text = self.format_conversation(conversation_history)
            
            # Generate assessment prompt
            prompt = self.get_assessment_prompt(conversation_text)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4o for better analysis
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Korean language assessor specializing in CEFR level evaluation. Provide clear, specific, and constructive assessments."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent assessments
                max_tokens=1000
            )
            
            assessment = response.choices[0].message.content.strip()
            return assessment
            
        except Exception as e:
            return f"❌ Error generating assessment: {e}"
