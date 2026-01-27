"""Handler for transcript-related events"""

from typing import Dict, Any
from .base_handler import BaseEventHandler


class TranscriptEventHandler(BaseEventHandler):
    """Handles user speech transcription events"""
    
    def can_handle(self, event_type: str) -> bool:
        """Handle transcript events"""
        return "transcription" in event_type.lower() or event_type == "conversation.item.output_audio_transcript.done"
    
    async def handle(self, event: Dict[str, Any]):
        """Process transcript events"""
        event_type = event.get("type")
        
        if event_type == "conversation.item.input_audio_transcription.completed":
            await self._handle_user_transcript(event)
        elif event_type == "conversation.item.output_audio_transcript.done":
            # This event fires when the AI's audio transcript is complete
            # We can check if a function was called here if needed
            pass
    
    async def _handle_user_transcript(self, event: Dict[str, Any]):
        """Handle completed user speech transcription"""
        session = self.get_from_context("session")
        assessment_state = self.get_from_context("assessment_state")
        
        transcript = event.get("transcript", "")
        print(f"👤 You: {transcript}")
        
        # Store in conversation history (only if not during assessment)
        if assessment_state.current_state.name == "INACTIVE":
            session.add_conversation_turn("User", transcript)
        else:
            # During assessment delivery, check for acknowledgment/goodbye
            if self._is_user_acknowledgment(transcript):
                print("✅ User acknowledged the report or said goodbye")
                session.user_acknowledged_report = True
                # If user acknowledges, we can end sooner
                print("\n👋 User acknowledged. Ending session gracefully...")
                session.should_end_session = True
                session.is_running = False
                # Note: In the full implementation, we'd need to signal the main loop
                # This will be handled by the orchestrator
    
    def _is_user_acknowledgment(self, transcript: str) -> bool:
        """
        Check if user's speech indicates acknowledgment or goodbye during assessment delivery.
        
        Args:
            transcript: The user's transcribed speech
            
        Returns:
            bool: True if user acknowledged or said goodbye
        """
        # Normalize transcript
        transcript_lower = transcript.lower().strip()
        
        # Korean acknowledgment keywords
        korean_keywords = [
            "감사합니다",  # Thank you
            "감사",        # Thanks
            "고마워",      # Thanks (informal)
            "고맙습니다",  # Thank you (formal)
            "알겠습니다",  # I understand
            "알겠어요",    # I understand (polite)
            "알았어요",    # Got it
            "네, 알겠습니다", # Yes, I understand
            "안녕히",      # Goodbye (part of goodbye phrases)
            "안녕",        # Bye
            "잘 가",       # Bye (informal)
            "수고하세요",  # Thank you for your work
            "좋아요",      # Good/Okay
            "괜찮아요",    # It's okay/good
        ]
        
        # English acknowledgment keywords (in case user switches to English)
        english_keywords = [
            "thank",
            "thanks",
            "bye",
            "goodbye",
            "got it",
            "understand",
            "okay",
            "ok",
            "great",
            "good",
            "see you",
        ]
        
        # Check Korean keywords
        for keyword in korean_keywords:
            if keyword in transcript_lower:
                return True
        
        # Check English keywords
        for keyword in english_keywords:
            if keyword in transcript_lower:
                return True
        
        return False
