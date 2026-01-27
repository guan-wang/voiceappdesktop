"""
Tool: Assessment guidance loader.
Reads the assess_prot.txt and returns assessment protocol text.
"""

import os
from typing import Optional

_GUIDANCE_CACHE: Optional[str] = None


def _load_assessment_protocol() -> str:
    """Load and normalize text from the assessment protocol file."""
    module_dir = os.path.dirname(os.path.abspath(__file__))
    txt_path = os.path.join(module_dir, "..", "resources", "assess_prot.txt")
    txt_path = os.path.normpath(txt_path)

    with open(txt_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    # Basic normalization
    normalized = " ".join(raw_text.split())
    return normalized.strip()


def read_guidance() -> str:
    """
    Return assessment guidance from assess_prot.txt, cached in memory.
    This function is called by the assessment agent to load scoring rubric and WLP Logic.
    """
    global _GUIDANCE_CACHE
    if _GUIDANCE_CACHE is None:
        _GUIDANCE_CACHE = _load_assessment_protocol()
        preview = _GUIDANCE_CACHE[:200]
        print(f"📋 Assessment protocol loaded (first 200 chars): {preview}")
    return _GUIDANCE_CACHE
