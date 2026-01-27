"""
SessionManager - Manages session state and conversation history
Centralizes all session-related data and flags
"""

import uuid
import os
import json
from datetime import datetime
from typing import List, Tuple


class SessionManager:
    """Manages session state, conversation history, and metadata"""
    
    def __init__(self):
        """Initialize session manager"""
        # Generate unique session ID for tracing
        self.session_id = str(uuid.uuid4())
        
        # Conversation tracking
        self.conversation_history: List[Tuple[str, str]] = []  # (speaker, text) tuples
        self.transcript_buffer = ""  # Buffer for accumulating transcript text
        
        # Session state flags
        self.is_running = False
        self.should_end_session = False
        self.user_acknowledged_report = False
        
        # Tool/function tracking
        self.guidance_loaded = False
        self.function_calls_made = []
        self.event_types_received = set()
        
        # Response tracking
        self.current_response_id = None
        
    def add_conversation_turn(self, speaker: str, text: str):
        """Add a conversation turn to history"""
        self.conversation_history.append((speaker, text))
    
    def get_conversation_history(self) -> List[Tuple[str, str]]:
        """Get a copy of the conversation history"""
        return self.conversation_history.copy()
    
    def track_function_call(self, function_name: str, event_type: str, **kwargs):
        """Track a function call for tracing"""
        function_call_info = {
            "function_name": function_name,
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            **kwargs
        }
        self.function_calls_made.append(function_call_info)
        print(f"📊 [TRACE] Function call tracked: {function_name} at {function_call_info['timestamp']}")
    
    def track_event_type(self, event_type: str):
        """Track an event type for debugging"""
        self.event_types_received.add(event_type)
    
    def save_assessment_report(self, report, verbal_summary: str):
        """Save assessment report to file for reference."""
        try:
            # Create reports directory if it doesn't exist
            reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
            os.makedirs(reports_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(reports_dir, f"assessment_{timestamp}.json")
            
            # Convert report to dict and save
            report_dict = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "report": report.model_dump(),
                "verbal_summary": verbal_summary,
                "conversation_length": len(self.conversation_history)
            }
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Assessment report saved to: {report_path}")
            
        except Exception as e:
            print(f"⚠️ Error saving report: {e}")
    
    def print_trace_summary(self):
        """Print tracing summary for debugging"""
        print(f"\n🔧 [DEBUG] All event types received: {sorted(self.event_types_received)}")
        if "response.function_call" in str(self.event_types_received):
            print("🔧 [DEBUG] Function call events were received!")
        else:
            print("🔧 [DEBUG] WARNING: No function call events detected!")
        
        # Print function call summary for tracing
        print(f"\n📊 [TRACE SUMMARY] Session ID: {self.session_id}")
        print(f"📊 [TRACE SUMMARY] Total function calls: {len(self.function_calls_made)}")
        if self.function_calls_made:
            print("📊 [TRACE SUMMARY] Function calls made:")
            for i, fc in enumerate(self.function_calls_made, 1):
                print(f"   {i}. {fc['function_name']} - {fc.get('event_type', 'unknown')} at {fc['timestamp']}")
        else:
            print("📊 [TRACE SUMMARY] ⚠️ No function calls were made in this session")
        print(f"📊 [TRACE SUMMARY] View this session in OpenAI logs: https://platform.openai.com/logs")
        print(f"📊 [TRACE SUMMARY] Filter by group_id: {self.session_id}")
    
    def reset(self):
        """Reset session state (useful for cleanup or restart)"""
        self.conversation_history.clear()
        self.transcript_buffer = ""
        self.is_running = False
        self.should_end_session = False
        self.user_acknowledged_report = False
        self.current_response_id = None
