"""
EventDispatcher - Routes events to appropriate handlers
Replaces long if/elif chains with clean handler routing
"""

from typing import Dict, Any, List
from handlers import (
    BaseEventHandler,
    AudioEventHandler,
    TranscriptEventHandler,
    FunctionEventHandler,
    ResponseEventHandler
)


class EventDispatcher:
    """Dispatches events to registered handlers"""
    
    def __init__(self, context: Dict[str, Any]):
        """
        Initialize dispatcher with context
        
        Args:
            context: Shared context containing managers, agents, websocket, etc.
        """
        self.context = context
        self.handlers: List[BaseEventHandler] = []
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register all default event handlers"""
        self.handlers = [
            AudioEventHandler(self.context),
            TranscriptEventHandler(self.context),
            FunctionEventHandler(self.context),
            ResponseEventHandler(self.context)
        ]
    
    def register_handler(self, handler: BaseEventHandler):
        """Register a custom event handler"""
        self.handlers.append(handler)
    
    async def dispatch(self, event: Dict[str, Any]):
        """
        Dispatch an event to the appropriate handler(s)
        
        Args:
            event: The event data from OpenAI Realtime API
        """
        event_type = event.get("type")
        if not event_type:
            print("⚠️ Event missing 'type' field")
            return
        
        # Track event type for debugging
        session = self.context.get("session")
        if session:
            session.track_event_type(event_type)
        
        # Find and invoke matching handlers
        handled = False
        for handler in self.handlers:
            if handler.can_handle(event_type):
                try:
                    await handler.handle(event)
                    handled = True
                except Exception as e:
                    print(f"❌ Error in {handler.__class__.__name__}: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Log unhandled events for debugging (optional)
        if not handled and not self._is_known_unhandled_event(event_type):
            # Uncomment for debugging: 
            # print(f"🔍 Unhandled event type: {event_type}")
            pass
    
    def _is_known_unhandled_event(self, event_type: str) -> bool:
        """Check if this is a known event type that we intentionally don't handle"""
        # Some events are informational and don't require handling
        known_unhandled = [
            "input_audio_buffer.speech_started",
            "input_audio_buffer.speech_stopped",
            "input_audio_buffer.committed",
            "conversation.item.created",
            "rate_limits.updated"
        ]
        return event_type in known_unhandled
