"""
Shared Agent Instances - Single instances reused across all sessions
Improves performance by loading resources once per server lifetime
"""

import sys
import os

# Add paths to import core modules (only if not already added)
# Go up 3 levels: shared_agents.py -> backend -> web -> project_root
backend_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.dirname(backend_dir)
core_parent_path = os.path.dirname(web_dir)

# Handle edge case where path might be root
if not core_parent_path or core_parent_path in ('/', '\\'):
    # Use relative path resolution
    core_parent_path = os.path.abspath(os.path.join(backend_dir, '..', '..'))

if core_parent_path not in sys.path:
    sys.path.insert(0, core_parent_path)
    print(f"📂 Added to sys.path: {core_parent_path}")

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
