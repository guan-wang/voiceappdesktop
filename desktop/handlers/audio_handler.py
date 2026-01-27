"""Handler for audio-related events"""

import base64
from typing import Dict, Any
from .base_handler import BaseEventHandler


class AudioEventHandler(BaseEventHandler):
    """Handles audio streaming events from OpenAI Realtime API"""
    
    def can_handle(self, event_type: str) -> bool:
        """Handle all audio-related events"""
        return event_type.startswith("response.audio")
    
    async def handle(self, event: Dict[str, Any]):
        """Process audio events"""
        event_type = event.get("type")
        
        if event_type == "response.audio.delta":
            await self._handle_audio_delta(event)
        elif event_type == "response.audio_transcript.delta":
            await self._handle_audio_transcript_delta(event)
        elif event_type == "response.audio_transcript.done":
            await self._handle_audio_transcript_done(event)
    
    async def _handle_audio_delta(self, event: Dict[str, Any]):
        """Handle incoming audio data from AI"""
        audio_manager = self.get_from_context("audio_manager")
        session = self.get_from_context("session")
        assessment_state = self.get_from_context("assessment_state")
        
        response_id = event.get("response_id", session.current_response_id)
        audio_data = event.get("delta", "")
        
        if audio_data:
            # Mark audio started (first delta received)
            if response_id and assessment_state.current_state.name != "INACTIVE":
                assessment_state.mark_audio_started(response_id)
            
            try:
                # Decode base64 audio
                audio_bytes = base64.b64decode(audio_data)
                
                # Track audio bytes for accurate duration calculation
                if response_id and assessment_state.current_state.name != "INACTIVE":
                    assessment_state.track_audio_bytes(response_id, len(audio_bytes))
                
                # Verify audio format (should be PCM16, 24kHz, mono)
                # Each sample is 2 bytes (16-bit), so audio_bytes length should be even
                if len(audio_bytes) % 2 != 0:
                    print(f"⚠️ Warning: Received odd-length audio chunk: {len(audio_bytes)} bytes")
                    # Pad with zero if odd length
                    audio_bytes += b'\x00'
                
                # Add to queue for playback
                audio_manager.queue_output_audio(audio_bytes)
            except Exception as e:
                print(f"⚠️ Error processing audio delta: {e}")
    
    async def _handle_audio_transcript_delta(self, event: Dict[str, Any]):
        """Accumulate AI's speech transcript"""
        session = self.get_from_context("session")
        delta = event.get("delta", "")
        if delta:
            session.transcript_buffer += delta
    
    async def _handle_audio_transcript_done(self, event: Dict[str, Any]):
        """Handle completion of AI's speech transcript"""
        session = self.get_from_context("session")
        assessment_state = self.get_from_context("assessment_state")
        
        response_id = event.get("response_id", session.current_response_id)
        
        # Print the complete sentence when done
        if session.transcript_buffer:
            ai_text = session.transcript_buffer
            print(f"🤖 AI: {ai_text}")
            # Store in conversation history (only if not during assessment)
            if assessment_state.current_state.name == "INACTIVE":
                session.add_conversation_turn("AI", ai_text)
            
            session.transcript_buffer = ""  # Reset buffer
        else:
            print()  # New line if buffer was empty
        
        # CRITICAL: Mark audio complete for this response using state machine
        # This fires when audio transcript is complete (audio is done!)
        if response_id and assessment_state.current_state.name != "INACTIVE":
            assessment_state.mark_audio_complete(response_id)
