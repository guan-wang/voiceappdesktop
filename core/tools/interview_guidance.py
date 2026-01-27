"""
Tool: Interview guidance loader.
Reads the interview_guide.txt and returns guidance text.
"""

import os
from typing import Optional

_GUIDANCE_CACHE: Optional[str] = None


def _load_guideline_text() -> str:
    """Load text from the interview guideline text file."""
    module_dir = os.path.dirname(os.path.abspath(__file__))
    txt_path = os.path.join(module_dir, "..", "resources", "interview_guide.txt")
    txt_path = os.path.normpath(txt_path)

    with open(txt_path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Basic normalization
    normalized = " ".join(raw.split())
    return normalized.strip()


def get_interview_guidance() -> str:
    """Return interview guidance from the text file, cached in memory."""
    global _GUIDANCE_CACHE
    if _GUIDANCE_CACHE is None:
        _GUIDANCE_CACHE = _load_guideline_text()
        preview = _GUIDANCE_CACHE[:200]
        print(f"🧭 Interview guidance loaded (first 200 chars): {preview}")
    return _GUIDANCE_CACHE
