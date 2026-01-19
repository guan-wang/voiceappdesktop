"""
Tool: Interview guidance loader.
Reads the interview_guideline.pdf and returns guidance text.
"""

import os
from typing import Optional
from pypdf import PdfReader

_GUIDANCE_CACHE: Optional[str] = None


def _load_guideline_text() -> str:
    """Load and normalize text from the PDF guideline."""
    module_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(module_dir, "..", "resources", "interview_guideline.pdf")
    pdf_path = os.path.normpath(pdf_path)

    reader = PdfReader(pdf_path)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

    raw = "\n".join(pages_text)
    # Basic normalization
    normalized = " ".join(raw.split())
    return normalized.strip()


def get_interview_guidance() -> str:
    """Return interview guidance from the PDF, cached in memory."""
    global _GUIDANCE_CACHE
    if _GUIDANCE_CACHE is None:
        _GUIDANCE_CACHE = _load_guideline_text()
        preview = _GUIDANCE_CACHE[:200]
        print(f"🧭 Interview guidance loaded (first 200 chars): {preview}")
    return _GUIDANCE_CACHE
