"""
Shared Agent Instances - Single instances reused across all sessions
Improves performance by loading resources once per server lifetime
"""

import sys
import os

# Add paths to import core modules (only if not already added)
# Try multiple possible project roots for Railway compatibility
backend_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.dirname(backend_dir)
local_root = os.path.dirname(web_dir)

# Possible project roots (Railway vs local)
possible_roots = [
    "/app",  # Railway standard
    local_root,  # Local development
]

# Add the first valid root that contains 'core' directory
for root in possible_roots:
    if root and root not in sys.path:
        core_path = os.path.join(root, "core")
        if os.path.isdir(core_path):
            sys.path.insert(0, root)
            print(f"📂 Added to sys.path: {root}")
            break

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
