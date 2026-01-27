"""
Validation tests for state machine integration in interview_agent.py
Tests the assessment delivery flow with proper state transitions
"""

import asyncio
from assessment_state_machine import AssessmentStateMachine, AssessmentState


class TestStateMachineBasics:
    """Test basic state machine functionality"""
    
    def test_initial_state(self):
        """Test that state machine starts in INACTIVE state"""
        sm = AssessmentStateMachine()
        assert sm.current_state == AssessmentState.INACTIVE
        assert not sm.is_complete()
    
    def test_trigger_assessment(self):
        """Test triggering assessment"""
        sm = AssessmentStateMachine()
        result = sm.trigger_assessment("User reached ceiling at A2")
        
        assert result is True
        assert sm.current_state == AssessmentState.TRIGGERED
        assert sm.assessment_reason == "User reached ceiling at A2"
    
    def test_trigger_assessment_duplicate(self):
        """Test that duplicate trigger is rejected"""
        sm = AssessmentStateMachine()
        sm.trigger_assessment("First trigger")
        result = sm.trigger_assessment("Duplicate trigger")
        
        assert result is False
        assert sm.current_state == AssessmentState.TRIGGERED  # Still in original state
    
    def test_acknowledgment_flow(self):
        """Test acknowledgment response flow"""
        sm = AssessmentStateMachine()
        sm.trigger_assessment("Test")
        
        # Start acknowledgment response
        sm.start_acknowledgment_response("resp_123")
        assert sm.current_state == AssessmentState.ACK_GENERATING
        assert "resp_123" in sm.response_trackers
        
        # Mark audio started
        sm.mark_audio_started("resp_123")
        assert sm.current_state == AssessmentState.ACK_SPEAKING
        
        # Mark audio complete
        sm.mark_audio_complete("resp_123")
        tracker = sm.response_trackers["resp_123"]
        assert tracker.audio_complete is True
        assert tracker.audio_event.is_set()
    
    def test_report_generation_check(self):
        """Test that report generation is allowed after acknowledgment"""
        sm = AssessmentStateMachine()
        sm.trigger_assessment("Test")
        sm.start_acknowledgment_response("resp_123")
        sm.mark_audio_started("resp_123")
        
        assert sm.can_proceed_to_report_generation() is True
        
        result = sm.start_report_generation()
        assert result is True
        assert sm.current_state == AssessmentState.REPORT_GENERATING
    
    def test_summary_flow(self):
        """Test summary response flow"""
        sm = AssessmentStateMachine()
        sm.trigger_assessment("Test")
        sm.start_acknowledgment_response("resp_123")
        sm.mark_audio_complete("resp_123")
        sm.start_report_generation()
        
        # Can't send summary until report is done
        assert sm.can_send_summary() is False
        
        # Mark ack audio complete (simulating wait completion)
        sm.response_trackers["resp_123"].audio_complete = True
        assert sm.can_send_summary() is True
        
        # Start summary
        sm.start_summary_response("resp_456", "Test summary")
        assert sm.current_state == AssessmentState.SUMMARY_SENDING
        assert sm.verbal_summary == "Test summary"
        
        # Audio starts
        sm.mark_audio_started("resp_456")
        assert sm.current_state == AssessmentState.SUMMARY_SPEAKING
        
        # Audio completes
        sm.mark_audio_complete("resp_456")
        assert sm.response_trackers["resp_456"].audio_complete is True
    
    def test_goodbye_flow(self):
        """Test goodbye response flow"""
        sm = AssessmentStateMachine()
        sm.trigger_assessment("Test")
        
        # Setup through summary
        sm.start_acknowledgment_response("resp_123")
        sm.mark_audio_complete("resp_123")
        sm.start_report_generation()
        sm.active_response_id = "resp_123"
        sm.start_summary_response("resp_456", "Summary")
        sm.mark_audio_complete("resp_456")
        
        # Can send goodbye
        assert sm.can_send_goodbye() is True
        
        sm.start_goodbye_response("resp_789")
        assert sm.current_state == AssessmentState.GOODBYE_SENDING
        
        sm.mark_audio_started("resp_789")
        assert sm.current_state == AssessmentState.GOODBYE_SPEAKING
        
        sm.mark_audio_complete("resp_789")
        
        # Mark complete
        sm.mark_complete()
        assert sm.current_state == AssessmentState.COMPLETE
        assert sm.is_complete() is True


class TestAsyncWaiting:
    """Test async waiting for audio completion"""
    
    async def test_wait_for_audio_immediate(self):
        """Test waiting when audio already complete"""
        sm = AssessmentStateMachine()
        sm.trigger_assessment("Test")
        sm.start_acknowledgment_response("resp_123")
        sm.mark_audio_complete("resp_123")
        
        # Should return immediately
        result = await sm.wait_for_audio_complete("resp_123", timeout=1.0)
        assert result is True
    
    async def test_wait_for_audio_delayed(self):
        """Test waiting for audio that arrives later"""
        sm = AssessmentStateMachine()
        sm.trigger_assessment("Test")
        sm.start_acknowledgment_response("resp_123")
        
        # Simulate audio arriving after delay
        async def complete_audio_later():
            await asyncio.sleep(0.1)
            sm.mark_audio_complete("resp_123")
        
        # Start both tasks
        complete_task = asyncio.create_task(complete_audio_later())
        wait_task = asyncio.create_task(
            sm.wait_for_audio_complete("resp_123", timeout=2.0)
        )
        
        result = await wait_task
        await complete_task
        
        assert result is True
    
    async def test_wait_for_audio_timeout(self):
        """Test timeout when audio never arrives"""
        sm = AssessmentStateMachine()
        sm.trigger_assessment("Test")
        sm.start_acknowledgment_response("resp_123")
        
        # Don't mark audio complete - should timeout
        result = await sm.wait_for_audio_complete("resp_123", timeout=0.1)
        assert result is False


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_unknown_response_audio_complete(self):
        """Test marking audio complete for unknown response"""
        sm = AssessmentStateMachine()
        # Should not crash
        sm.mark_audio_complete("unknown_response")
    
    async def test_wait_for_unknown_response(self):
        """Test waiting for unknown response"""
        sm = AssessmentStateMachine()
        result = await sm.wait_for_audio_complete("unknown", timeout=0.1)
        assert result is False
    
    def test_invalid_state_transitions(self):
        """Test that invalid transitions are prevented"""
        sm = AssessmentStateMachine()
        
        # Can't start report without triggering assessment
        result = sm.start_report_generation()
        assert result is False
        
        # Can't send summary without generating report
        assert sm.can_send_summary() is False
        
        # Can't send goodbye without summary
        assert sm.can_send_goodbye() is False


class TestStateTracking:
    """Test state tracking and response tracking"""
    
    def test_response_tracker_creation(self):
        """Test that response trackers are created correctly"""
        sm = AssessmentStateMachine()
        sm.trigger_assessment("Test")
        sm.start_acknowledgment_response("resp_123")
        
        assert "resp_123" in sm.response_trackers
        tracker = sm.response_trackers["resp_123"]
        assert tracker.response_id == "resp_123"
        assert tracker.state == AssessmentState.ACK_GENERATING
        assert tracker.audio_started is False
        assert tracker.audio_complete is False
    
    def test_active_response_tracking(self):
        """Test that active response ID is updated"""
        sm = AssessmentStateMachine()
        sm.trigger_assessment("Test")
        
        sm.start_acknowledgment_response("resp_123")
        assert sm.active_response_id == "resp_123"
        
        sm.mark_audio_complete("resp_123")
        sm.start_report_generation()
        sm.start_summary_response("resp_456", "Summary")
        assert sm.active_response_id == "resp_456"
    
    def test_state_summary(self):
        """Test getting state summary for debugging"""
        sm = AssessmentStateMachine()
        sm.trigger_assessment("Test reason")
        sm.start_acknowledgment_response("resp_123")
        sm.mark_audio_started("resp_123")
        
        summary = sm.get_state_summary()
        
        assert "ACK_GENERATING" in summary
        assert "resp_123" in summary
        assert "audio_started=True" in summary


def run_validation():
    """Run all validation tests and report results"""
    print("=" * 70)
    print("STATE MACHINE INTEGRATION VALIDATION")
    print("=" * 70)
    
    test_classes = [
        TestStateMachineBasics,
        TestAsyncWaiting,
        TestErrorHandling,
        TestStateTracking
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n[TEST] Running {test_class.__name__}...")
        test_instance = test_class()
        
        for method_name in dir(test_instance):
            if method_name.startswith("test_"):
                total_tests += 1
                method = getattr(test_instance, method_name)
                
                try:
                    # Handle async methods
                    if asyncio.iscoroutinefunction(method):
                        asyncio.run(method())
                    else:
                        method()
                    
                    passed_tests += 1
                    print(f"  [PASS] {method_name}")
                except Exception as e:
                    failed_tests.append((test_class.__name__, method_name, str(e)))
                    print(f"  [FAIL] {method_name}: {e}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} [PASS]")
    print(f"Failed: {len(failed_tests)} [FAIL]")
    
    if failed_tests:
        print("\n[FAIL] Failed Tests:")
        for class_name, method_name, error in failed_tests:
            print(f"  - {class_name}.{method_name}: {error}")
        return False
    else:
        print("\n[PASS] ALL TESTS PASSED!")
        return True


if __name__ == "__main__":
    success = run_validation()
    exit(0 if success else 1)
