"""Base class for event handlers"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseEventHandler(ABC):
    """Base class for all event handlers"""
    
    def __init__(self, context: Dict[str, Any]):
        """
        Initialize handler with context
        
        Args:
            context: Shared context containing references to managers, agents, etc.
        """
        self.context = context
    
    @abstractmethod
    def can_handle(self, event_type: str) -> bool:
        """
        Check if this handler can process the given event type
        
        Args:
            event_type: The type of event (e.g., 'response.audio.delta')
            
        Returns:
            bool: True if this handler can process the event
        """
        pass
    
    @abstractmethod
    async def handle(self, event: Dict[str, Any]):
        """
        Process the event
        
        Args:
            event: The event data from OpenAI Realtime API
        """
        pass
    
    def get_from_context(self, key: str, default=None):
        """Helper to safely get values from context"""
        return self.context.get(key, default)
