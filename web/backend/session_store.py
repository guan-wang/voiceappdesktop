"""
Session Store - Manages multiple user sessions
Tracks active interviews and their state
"""

import uuid
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import asyncio


class UserSession:
    """Represents a single user's interview session"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        
        # Conversation tracking
        self.conversation_history: List[Tuple[str, str]] = []
        self.transcript_buffer = ""
        
        # Session state
        self.is_active = False
        self.should_end = False
        self.user_acknowledged_report = False
        
        # OpenAI connection
        self.openai_websocket = None
        self.openai_task = None
        
        # Assessment state (will be initialized with AssessmentStateMachine)
        self.assessment_state = None
    
    def save_assessment_report(self, report, verbal_summary: str):
        """Save assessment report to file"""
        try:
            import os
            import json
            from datetime import datetime
            
            # Create reports directory
            reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
            os.makedirs(reports_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(reports_dir, f"web_assessment_{timestamp}.json")
            
            # Save report
            report_dict = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "report": report.model_dump() if hasattr(report, 'model_dump') else report,
                "verbal_summary": verbal_summary,
                "conversation_length": len(self.conversation_history)
            }
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Assessment report saved: {report_path}")
            
        except Exception as e:
            print(f"⚠️ Error saving assessment report: {e}")
        
        # Function tracking
        self.guidance_loaded = False
        self.function_calls_made = []
        
    def add_conversation_turn(self, speaker: str, text: str):
        """Add a conversation turn"""
        self.conversation_history.append((speaker, text))
        self.last_activity = datetime.now()
    
    def get_conversation_history(self) -> List[Tuple[str, str]]:
        """Get conversation history"""
        return self.conversation_history.copy()
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def is_stale(self, timeout_minutes: int = 30) -> bool:
        """Check if session is stale (inactive for too long)"""
        elapsed = (datetime.now() - self.last_activity).total_seconds() / 60
        return elapsed > timeout_minutes


class SessionStore:
    """Global store for managing all active sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self._cleanup_task = None
    
    def create_session(self) -> UserSession:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        session = UserSession(session_id)
        self.sessions[session_id] = session
        print(f"✅ Created session: {session_id[:8]}...")
        return session
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get an existing session"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """Remove a session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            # Cleanup OpenAI connection
            if session.openai_websocket:
                try:
                    asyncio.create_task(session.openai_websocket.close())
                except Exception as e:
                    print(f"⚠️ Error closing OpenAI websocket: {e}")
            
            if session.openai_task and not session.openai_task.done():
                session.openai_task.cancel()
            
            del self.sessions[session_id]
            print(f"🗑️ Removed session: {session_id[:8]}...")
    
    async def cleanup_stale_sessions(self):
        """Periodically clean up stale sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                stale_sessions = [
                    sid for sid, session in self.sessions.items()
                    if session.is_stale()
                ]
                
                for session_id in stale_sessions:
                    print(f"🧹 Cleaning up stale session: {session_id[:8]}...")
                    self.remove_session(session_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Error in cleanup task: {e}")
    
    def start_cleanup_task(self):
        """Start the background cleanup task"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self.cleanup_stale_sessions())
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.sessions)


# Global session store instance
session_store = SessionStore()
