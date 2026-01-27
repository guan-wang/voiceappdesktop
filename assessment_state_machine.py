"""
Assessment State Machine - Robust state management for assessment delivery
Replaces fragile counter-based approach with explicit state tracking
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
import asyncio


class AssessmentState(Enum):
    """States during assessment delivery"""
    INACTIVE = "inactive"  # Not in assessment mode
    TRIGGERED = "triggered"  # Assessment just triggered
    ACK_GENERATING = "ack_generating"  # Waiting for acknowledgment response
    ACK_SPEAKING = "ack_speaking"  # Acknowledgment audio playing
    REPORT_GENERATING = "report_generating"  # Generating assessment report
    SUMMARY_SENDING = "summary_sending"  # Sending summary to be spoken
    SUMMARY_SPEAKING = "summary_speaking"  # Summary audio playing
    GOODBYE_SENDING = "goodbye_sending"  # Sending goodbye message
    GOODBYE_SPEAKING = "goodbye_speaking"  # Goodbye audio playing
    COMPLETE = "complete"  # All done


@dataclass
class ResponseTracker:
    """Track a specific response by ID"""
    response_id: str
    state: AssessmentState
    audio_started: bool = False
    audio_complete: bool = False
    response_complete: bool = False
    audio_event: asyncio.Event = None
    audio_bytes_received: int = 0  # Track total audio bytes for duration calculation
    
    def __post_init__(self):
        if self.audio_event is None:
            self.audio_event = asyncio.Event()
    
    def calculate_audio_duration(self) -> float:
        """Calculate actual audio duration from received bytes.
        
        Audio format: 16-bit PCM, 24kHz, mono
        Duration = total_bytes / (sample_rate * channels * bytes_per_sample)
                 = total_bytes / (24000 * 1 * 2)
                 = total_bytes / 48000
        """
        if self.audio_bytes_received == 0:
            return 0.0
        return self.audio_bytes_received / 48000.0  # seconds


class AssessmentStateMachine:
    """
    Manages assessment delivery state transitions with proper synchronization.
    
    Key improvements over counter-based approach:
    1. Explicit states with clear transitions
    2. Response ID tracking (not just counts)
    3. Separate audio from response completion
    4. No race conditions from premature state updates
    """
    
    def __init__(self):
        self.current_state = AssessmentState.INACTIVE
        self.response_trackers = {}  # response_id -> ResponseTracker
        self.active_response_id: Optional[str] = None
        self.assessment_reason = ""
        self.verbal_summary = ""
        
    def trigger_assessment(self, reason: str):
        """Trigger assessment - move to TRIGGERED state"""
        if self.current_state != AssessmentState.INACTIVE:
            print(f"[WARN] Assessment already triggered (state: {self.current_state})")
            return False
        
        self.current_state = AssessmentState.TRIGGERED
        self.assessment_reason = reason
        print(f"[STATE] {self.current_state.value}")
        return True
    
    def start_acknowledgment_response(self, response_id: str):
        """
        Acknowledgment response created - move to ACK_GENERATING
        
        Args:
            response_id: The response ID from OpenAI
        """
        if self.current_state != AssessmentState.TRIGGERED:
            print(f"[WARN] Unexpected ack response in state: {self.current_state}")
            return
        
        self.current_state = AssessmentState.ACK_GENERATING
        self.active_response_id = response_id
        self.response_trackers[response_id] = ResponseTracker(
            response_id=response_id,
            state=AssessmentState.ACK_GENERATING
        )
        print(f"[STATE] {self.current_state.value} (ID: {response_id[-8:]})")
    
    def mark_audio_started(self, response_id: str):
        """Audio started for a response"""
        if response_id in self.response_trackers:
            self.response_trackers[response_id].audio_started = True
            
            # Update state based on which response this is
            if self.current_state == AssessmentState.ACK_GENERATING:
                self.current_state = AssessmentState.ACK_SPEAKING
                print(f"[STATE] {self.current_state.value}")
            elif self.current_state == AssessmentState.SUMMARY_SENDING:
                self.current_state = AssessmentState.SUMMARY_SPEAKING
                print(f"[STATE] {self.current_state.value}")
            elif self.current_state == AssessmentState.GOODBYE_SENDING:
                self.current_state = AssessmentState.GOODBYE_SPEAKING
                print(f"[STATE] {self.current_state.value}")
    
    def track_audio_bytes(self, response_id: str, bytes_count: int):
        """Track audio bytes received for duration calculation"""
        if response_id in self.response_trackers:
            self.response_trackers[response_id].audio_bytes_received += bytes_count
    
    def mark_audio_complete(self, response_id: str):
        """
        Audio transcript complete for a response.
        This is the TRUE signal that audio finished playing.
        """
        if response_id not in self.response_trackers:
            print(f"[WARN] Audio complete for unknown response: {response_id[-8:]}")
            return
        
        tracker = self.response_trackers[response_id]
        tracker.audio_complete = True
        tracker.audio_event.set()  # Signal waiting coroutines
        
        print(f"[DONE] Audio complete for {tracker.state.value} (ID: {response_id[-8:]})")
    
    def mark_response_complete(self, response_id: str):
        """
        Response.done event fired - response is complete from API's perspective.
        NOTE: This does NOT mean audio is complete!
        """
        if response_id not in self.response_trackers:
            # This might be a normal conversation response before assessment
            return
        
        tracker = self.response_trackers[response_id]
        tracker.response_complete = True
        print(f"[DONE] Response complete for {tracker.state.value} (ID: {response_id[-8:]})")
    
    async def wait_for_audio_complete(self, response_id: str, timeout: float = 15.0) -> bool:
        """
        Wait for audio to complete for a specific response.
        
        Returns:
            True if audio completed, False if timeout
        """
        if response_id not in self.response_trackers:
            print(f"[WARN] Cannot wait for unknown response: {response_id[-8:]}")
            return False
        
        tracker = self.response_trackers[response_id]
        
        # If already complete, return immediately
        if tracker.audio_complete:
            return True
        
        # Wait for audio event
        try:
            await asyncio.wait_for(tracker.audio_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            print(f"[WARN] Timeout waiting for audio: {tracker.state.value}")
            return False
    
    def can_proceed_to_report_generation(self) -> bool:
        """
        Check if we can proceed to report generation.
        We should be in ACK_GENERATING or ACK_SPEAKING state.
        """
        return self.current_state in [
            AssessmentState.ACK_GENERATING,
            AssessmentState.ACK_SPEAKING
        ]
    
    def start_report_generation(self):
        """Start generating assessment report"""
        if not self.can_proceed_to_report_generation():
            print(f"[WARN] Cannot generate report in state: {self.current_state}")
            return False
        
        self.current_state = AssessmentState.REPORT_GENERATING
        print(f"[STATE] {self.current_state.value}")
        return True
    
    def can_send_summary(self) -> bool:
        """Check if acknowledgment audio completed and we can send summary"""
        # We should have finished report generation
        if self.current_state != AssessmentState.REPORT_GENERATING:
            return False
        
        # Acknowledgment audio should be complete
        if not self.active_response_id:
            return False
        
        tracker = self.response_trackers.get(self.active_response_id)
        return tracker and tracker.audio_complete
    
    def start_summary_response(self, response_id: str, verbal_summary: str):
        """Summary response created"""
        self.current_state = AssessmentState.SUMMARY_SENDING
        self.active_response_id = response_id
        self.verbal_summary = verbal_summary
        self.response_trackers[response_id] = ResponseTracker(
            response_id=response_id,
            state=AssessmentState.SUMMARY_SENDING
        )
        print(f"[STATE] {self.current_state.value} (ID: {response_id[-8:]})")
    
    def can_send_goodbye(self) -> bool:
        """Check if summary audio completed and we can send goodbye"""
        if self.current_state not in [
            AssessmentState.SUMMARY_SENDING,
            AssessmentState.SUMMARY_SPEAKING
        ]:
            return False
        
        # Summary audio should be complete
        tracker = self.response_trackers.get(self.active_response_id)
        return tracker and tracker.audio_complete
    
    def start_goodbye_response(self, response_id: str):
        """Goodbye response created"""
        self.current_state = AssessmentState.GOODBYE_SENDING
        self.active_response_id = response_id
        self.response_trackers[response_id] = ResponseTracker(
            response_id=response_id,
            state=AssessmentState.GOODBYE_SENDING
        )
        print(f"[STATE] {self.current_state.value} (ID: {response_id[-8:]})")
    
    def mark_complete(self):
        """Assessment delivery complete"""
        self.current_state = AssessmentState.COMPLETE
        print(f"[STATE] {self.current_state.value}")
    
    def is_complete(self) -> bool:
        """Check if assessment is complete"""
        return self.current_state == AssessmentState.COMPLETE
    
    def get_state_summary(self) -> str:
        """Get a summary of current state for debugging"""
        lines = [
            f"Current State: {self.current_state.value}",
            f"Active Response: {self.active_response_id[-8:] if self.active_response_id else 'None'}",
            f"Tracked Responses: {len(self.response_trackers)}"
        ]
        
        for response_id, tracker in self.response_trackers.items():
            lines.append(
                f"  - {response_id[-8:]}: {tracker.state.value} "
                f"(audio_started={tracker.audio_started}, "
                f"audio_complete={tracker.audio_complete}, "
                f"response_complete={tracker.response_complete})"
            )
        
        return "\n".join(lines)
