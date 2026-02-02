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
            
            # Determine reports directory
            # Railway: Volume mounted at /app/backend/reports
            # Local: web/backend/reports
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Check if we're on Railway (volume mount exists)
            railway_reports = "/app/backend/reports"
            if os.path.exists(railway_reports) and os.path.isdir(railway_reports):
                reports_dir = railway_reports
                print(f"📂 [{self.session_id[:8]}] Using Railway volume: {reports_dir}")
            else:
                # Local development
                reports_dir = os.path.join(backend_dir, "reports")
            
            os.makedirs(reports_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(reports_dir, f"web_assessment_{timestamp}.json")
            
            # Format conversation history for the report
            conversation_transcript = []
            for speaker, text in self.conversation_history:
                conversation_transcript.append({
                    "speaker": speaker,
                    "text": text
                })
            
            # Save report with survey structure
            report_dict = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "report": report.model_dump() if hasattr(report, 'model_dump') else report,
                "verbal_summary": verbal_summary,
                "conversation_history": conversation_transcript,
                "conversation_length": len(self.conversation_history),
                "survey": {
                    "completed": False,
                    "completed_at": None,
                    "responses": {
                        "comfort_level": None,
                        "feedback_usefulness": None,
                        "name": None,
                        "email": None
                    }
                }
            }
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
            print(f"💾 [{self.session_id[:8]}] Saved: {report_path}")
            
        except Exception as e:
            print(f"⚠️ [{self.session_id[:8]}] Save failed: {e}")
            import traceback
            traceback.print_exc()
        
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
        print(f"✅ Session {session_id[:8]}")
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
                    print(f"🧹 Stale session {session_id[:8]}")
                    self.remove_session(session_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Error in cleanup task: {e}")
    
    def start_cleanup_task(self):
        """Start the background cleanup task"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self.cleanup_stale_sessions())
    
    async def shutdown_all_sessions(self):
        """Shutdown all active sessions and cancel their tasks"""
        session_count = len(self.sessions)
        if session_count == 0:
            return
        
        print(f"🧹 Shutting down {session_count} session(s)...")
        
        # Cancel cleanup task first
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        
        # Close all sessions with timeout
        session_ids = list(self.sessions.keys())
        cleanup_tasks = []
        
        for session_id in session_ids:
            session = self.sessions.get(session_id)
            if session:
                cleanup_tasks.append(self._cleanup_single_session(session, session_id))
        
        # Wait for all cleanups with timeout
        if cleanup_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True),
                    timeout=3.0
                )
            except asyncio.TimeoutError:
                print("⚠️ Some sessions didn't cleanup in time")
        
        # Force clear any remaining sessions
        self.sessions.clear()
    
    async def _cleanup_single_session(self, session, session_id):
        """Cleanup a single session"""
        try:
            # Cancel OpenAI task
            if session.openai_task and not session.openai_task.done():
                session.openai_task.cancel()
                try:
                    await asyncio.wait_for(session.openai_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            
            # Close OpenAI websocket
            if session.openai_websocket:
                try:
                    await session.openai_websocket.close()
                except Exception:
                    pass
            
            # Remove from store
            if session_id in self.sessions:
                del self.sessions[session_id]
                
        except Exception as e:
            print(f"⚠️ Error cleaning session {session_id[:8]}: {e}")
    
    def append_survey_to_assessment(self, session_id: str, survey_data: dict):
        """Append survey responses to existing assessment file"""
        import glob
        import os
        import json
        from datetime import datetime
        
        # Determine reports directory (same logic as save_assessment_report)
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Check if we're on Railway (volume mount exists)
        railway_reports = "/app/backend/reports"
        if os.path.exists(railway_reports) and os.path.isdir(railway_reports):
            reports_dir = railway_reports
        else:
            # Local development
            reports_dir = os.path.join(backend_dir, "reports")
        
        # Find the assessment file for this session
        pattern = os.path.join(reports_dir, "web_assessment_*.json")
        files = glob.glob(pattern)
        
        # Find file matching session_id
        target_file = None
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('session_id') == session_id:
                        target_file = filepath
                        break
            except Exception as e:
                print(f"⚠️ Error reading {filepath}: {e}")
                continue
        
        if not target_file:
            raise FileNotFoundError(f"No assessment found for session {session_id}")
        
        # Read existing data
        with open(target_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Add survey data
        data['survey'] = {
            "completed": True,
            "completed_at": datetime.now().isoformat(),
            "responses": {
                "comfort_level": survey_data.get("comfort_level"),
                "feedback_usefulness": survey_data.get("feedback_usefulness"),
                "name": survey_data.get("name", "").strip(),
                "email": survey_data.get("email", "").strip()
            }
        }
        
        # Atomic write with temp file
        temp_path = target_file + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Atomic rename (safe even if process crashes)
        os.replace(temp_path, target_file)
        
        print(f"💾 [{session_id[:8]}] Survey appended: {target_file}")
        
        return target_file
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.sessions)


# Global session store instance
session_store = SessionStore()
