"""
Shared prompt loaders for Korean Voice Tutor.
Used by both web and desktop platforms.
"""

import os
from typing import Optional

_INTERVIEW_SYSTEM_PROMPT_CACHE: Optional[str] = None


def load_interview_system_prompt() -> str:
    """
    Load the canonical interview system prompt from core/resources/.
    Cached in memory after first load.
    """
    global _INTERVIEW_SYSTEM_PROMPT_CACHE
    if _INTERVIEW_SYSTEM_PROMPT_CACHE is None:
        module_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(module_dir, "resources", "interview_system_prompt.txt")
        prompt_path = os.path.normpath(prompt_path)

        with open(prompt_path, "r", encoding="utf-8") as f:
            _INTERVIEW_SYSTEM_PROMPT_CACHE = f.read().strip()

    return _INTERVIEW_SYSTEM_PROMPT_CACHE
