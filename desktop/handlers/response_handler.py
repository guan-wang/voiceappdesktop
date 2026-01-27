"""Handler for response lifecycle events"""

import asyncio
import json
from typing import Dict, Any
from .base_handler import BaseEventHandler
from assessment_state_machine import AssessmentState


class ResponseEventHandler(BaseEventHandler):
    """Handles response lifecycle events (created, done, etc.)"""
    
    def can_handle(self, event_type: str) -> bool:
        """Handle response lifecycle events"""
        return event_type in [
            "response.created",
            "response.done",
            "session.created",
            "session.updated",
            "error",
            "conversation.item.creation_failed"
        ]
    
    async def handle(self, event: Dict[str, Any]):
        """Process response lifecycle events"""
        event_type = event.get("type")
        
        if event_type == "session.created":
            print("✅ Session created successfully")
        elif event_type == "session.updated":
            print("✅ Session updated")
        elif event_type == "response.created":
            await self._handle_response_created(event)
        elif event_type == "response.done":
            await self._handle_response_done(event)
        elif event_type == "error":
            self._handle_error(event)
        elif event_type == "conversation.item.creation_failed":
            self._handle_creation_failed(event)
    
    async def _handle_response_created(self, event: Dict[str, Any]):
        """Handle response creation - track response ID"""
        session = self.get_from_context("session")
        assessment_state = self.get_from_context("assessment_state")
        
        response_id = event.get("response", {}).get("id")
        if response_id:
            session.current_response_id = response_id
            
            # Register with state machine based on current state
            current_state = assessment_state.current_state
            if current_state == AssessmentState.TRIGGERED:
                assessment_state.start_acknowledgment_response(response_id)
            elif current_state == AssessmentState.REPORT_GENERATING:
                # Summary response being created
                verbal_summary = assessment_state.verbal_summary
                if verbal_summary:
                    assessment_state.start_summary_response(response_id, verbal_summary)
            elif current_state in [AssessmentState.SUMMARY_SPEAKING, AssessmentState.SUMMARY_SENDING]:
                # Check if summary audio completed - if so, this is goodbye response
                tracker = assessment_state.response_trackers.get(assessment_state.active_response_id)
                if tracker and tracker.audio_complete:
                    # This is goodbye response
                    assessment_state.start_goodbye_response(response_id)
    
    async def _handle_response_done(self, event: Dict[str, Any]):
        """Handle response completion - coordinate assessment flow"""
        session = self.get_from_context("session")
        assessment_state = self.get_from_context("assessment_state")
        assessment_agent = self.get_from_context("assessment_agent")
        websocket = self.get_from_context("websocket")
        
        # Get response ID from event, or use the tracked current response ID
        response_id = event.get("response_id") or session.current_response_id or "unknown"
        print(f"✅ Response complete (ID: {response_id[-8:] if response_id != 'unknown' else response_id})")
        
        # Mark response complete in state machine
        if response_id and response_id != "unknown":
            assessment_state.mark_response_complete(response_id)
        
        # Handle based on current state
        current_state = assessment_state.current_state
        
        if current_state in [AssessmentState.ACK_GENERATING, AssessmentState.ACK_SPEAKING]:
            await self._handle_acknowledgment_complete(response_id, websocket, assessment_state, 
                                                      assessment_agent, session)
        
        elif current_state in [AssessmentState.SUMMARY_SENDING, AssessmentState.SUMMARY_SPEAKING]:
            await self._handle_summary_complete(response_id, websocket, assessment_state)
        
        elif current_state in [AssessmentState.GOODBYE_SENDING, AssessmentState.GOODBYE_SPEAKING]:
            await self._handle_goodbye_complete(response_id, assessment_state, session)
        
        # Check if user acknowledged early
        if session.user_acknowledged_report and not assessment_state.is_complete():
            print("\n✅ User acknowledged during assessment. Ending session...")
            assessment_state.mark_complete()
            session.should_end_session = True
            session.is_running = False
    
    async def _handle_acknowledgment_complete(self, response_id: str, websocket, 
                                             assessment_state, assessment_agent, session):
        """Handle completion of acknowledgment response"""
        print("⏳ Waiting for acknowledgment audio to complete...")
        audio_ok = await assessment_state.wait_for_audio_complete(response_id, timeout=10.0)
        
        current_state = assessment_state.current_state
        if audio_ok or current_state == AssessmentState.ACK_SPEAKING:
            # Start generating report in background to avoid blocking websocket
            if assessment_state.start_report_generation():
                print("\n🔍 Generating assessment report in background...")
                
                # Create background task for assessment generation
                async def generate_and_send_assessment():
                    try:
                        # Generate assessment report (this takes time)
                        report = assessment_agent.generate_assessment(session.get_conversation_history())
                        verbal_summary = assessment_agent.report_to_verbal_summary(report)
                        print(f"\n📋 Assessment Summary:\n{verbal_summary}")
                        
                        # Save report to file
                        session.save_assessment_report(report, verbal_summary)
                        
                        # Store summary in state machine
                        assessment_state.verbal_summary = verbal_summary
                        
                        # Send summary to be spoken (in English)
                        print("\n🗣️ Sending assessment summary to be spoken...")
                        await self._send_text_message(websocket, verbal_summary, language="english")
                    except Exception as e:
                        print(f"❌ Error in assessment generation: {e}")
                
                # Launch as background task so event loop continues
                asyncio.create_task(generate_and_send_assessment())
        else:
            print("⚠️ Acknowledgment audio timeout, but proceeding with report generation")
    
    async def _handle_summary_complete(self, response_id: str, websocket, assessment_state):
        """Handle completion of summary response"""
        print("⏳ Waiting for summary audio to complete...")
        audio_ok = await assessment_state.wait_for_audio_complete(response_id, timeout=20.0)
        
        current_state = assessment_state.current_state
        if audio_ok or current_state == AssessmentState.SUMMARY_SPEAKING:
            # Use actual audio duration from received bytes
            tracker = assessment_state.response_trackers.get(response_id)
            if tracker:
                actual_duration = tracker.calculate_audio_duration()
                buffer_delay = actual_duration + 3.0
                print(f"⏳ Ensuring audio playback buffer is fully drained (actual {actual_duration:.1f}s + 3.0s buffer = {buffer_delay:.1f}s)...")
            else:
                # Fallback to word-based estimation
                verbal_summary = assessment_state.verbal_summary or ""
                word_count = len(verbal_summary.split())
                estimated_duration = (word_count / 2.5) + 3.0
                buffer_delay = max(5.0, min(estimated_duration, 30.0))
                print(f"⏳ Ensuring audio playback buffer is fully drained (estimated {buffer_delay:.1f}s for {word_count} words)...")
            
            await asyncio.sleep(buffer_delay)
            
            # Check if we can send goodbye
            if assessment_state.can_send_goodbye():
                print("\n👋 Sending goodbye message...")
                goodbye_msg = "Thank you for completing the interview! Keep practicing, and you'll continue to improve. Goodbye!"
                await self._send_text_message(websocket, goodbye_msg, language="english")
        else:
            print("⚠️ Summary audio timeout, but proceeding with goodbye")
    
    async def _handle_goodbye_complete(self, response_id: str, assessment_state, session):
        """Handle completion of goodbye response"""
        print("⏳ Waiting for goodbye audio to complete...")
        audio_ok = await assessment_state.wait_for_audio_complete(response_id, timeout=10.0)
        
        # Wait additional time for audio buffer to drain
        print("⏳ Ensuring goodbye audio playback buffer is fully drained...")
        await asyncio.sleep(3.0)
        
        # Mark assessment complete
        assessment_state.mark_complete()
        
        # End session
        print("\n✅ Assessment delivery complete. Ending session...")
        session.should_end_session = True
        session.is_running = False
    
    def _handle_error(self, event: Dict[str, Any]):
        """Handle API errors"""
        error = event.get("error", {})
        print(f"❌ API Error: {error.get('message', 'Unknown error')}")
    
    def _handle_creation_failed(self, event: Dict[str, Any]):
        """Handle item creation failures"""
        error = event.get("error", {})
        print(f"⚠️ Item creation failed: {error.get('message', 'Unknown error')}")
    
    async def _send_text_message(self, websocket, text: str, language: str = "auto"):
        """Send a text message for the AI to speak using response.create with instructions."""
        preview = text[:100] + "..." if len(text) > 100 else text
        print(f"   📤 Sending to be spoken: \"{preview}\"")
        
        # Determine language instruction
        if language == "english":
            lang_instruction = "Speak this in natural American English pronunciation: "
        elif language == "korean":
            lang_instruction = "Speak this in Korean: "
        else:
            # Auto-detect
            ascii_ratio = sum(1 for c in text if ord(c) < 128) / len(text) if text else 0
            if ascii_ratio > 0.7:
                lang_instruction = "Speak this in natural American English pronunciation: "
            else:
                lang_instruction = "Speak this naturally: "
        
        # Use response.create with instructions
        response_event = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "instructions": f"{lang_instruction}{text}"
            }
        }
        await websocket.send(json.dumps(response_event))
