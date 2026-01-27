"""
Debug script to test which audio events fire and when.
Add this code to your event_handler temporarily to see event timing.
"""

# Add to InterviewAgent.__init__:
self.audio_event_log = []

# Add to event_handler, right after parsing event:
if event_type in [
    "response.audio.done",
    "response.audio_transcript.done",
    "response.done"
]:
    import time
    log_entry = {
        "time": time.time(),
        "event_type": event_type,
        "response_id": event.get("response_id", "unknown"),
        "item_id": event.get("item_id", "unknown"),
        "assessment_completed": self.assessment_responses_completed
    }
    self.audio_event_log.append(log_entry)
    
    print(f"\n🔍 [AUDIO EVENT] {event_type}")
    print(f"   Response ID: {log_entry['response_id'][-8:] if log_entry['response_id'] != 'unknown' else 'unknown'}")
    print(f"   Assessment responses completed: {self.assessment_responses_completed}")
    print(f"   Time: {log_entry['time']}")

# At the end of run() method, add:
print("\n" + "="*50)
print("AUDIO EVENT TIMELINE")
print("="*50)
if self.audio_event_log:
    start_time = self.audio_event_log[0]["time"]
    for entry in self.audio_event_log:
        elapsed = entry["time"] - start_time
        print(f"+{elapsed:6.2f}s | {entry['event_type']:35s} | Response: {entry['response_id'][-8:] if entry['response_id'] != 'unknown' else 'unknown':8s} | Completed: {entry['assessment_completed']}")
print("="*50)
```
