"""
Shared Agent Instances - Single instances reused across all sessions
Improves performance by loading resources once per server lifetime
"""

import sys
import os

# Add paths to import core modules (only if not already added)
core_parent_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if core_parent_path not in sys.path:
    sys.path.insert(0, core_parent_path)

from core import AssessmentAgent


# Shared assessment agent instance (created once, reused by all sessions)
# System prompt loaded once at initialization, cached in memory
_shared_assessment_agent: AssessmentAgent = None


def get_assessment_agent() -> AssessmentAgent:
    """
    Get the shared assessment agent instance.
    Creates it on first call, then reuses the same instance.
    
    Returns:
        AssessmentAgent: Shared assessment agent instance
    """
    global _shared_assessment_agent
    
    if _shared_assessment_agent is None:
        _shared_assessment_agent = AssessmentAgent()
    
    return _shared_assessment_agent
