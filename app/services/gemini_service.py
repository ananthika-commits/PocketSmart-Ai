"""
Gemini Service layer for PocketSmart AI.
Wraps core logic from gemini_utils for modular architecture compatibility.
"""
from gemini_utils import (
    generate_recommendations,
    generate_platform_url,
    _generate_dynamic_fallback,
    _build_prompt,
    _extract_json,
    _clean_json,
)

__all__ = [
    "generate_recommendations",
    "generate_platform_url",
    "_generate_dynamic_fallback",
    "_build_prompt",
    "_extract_json",
    "_clean_json",
]
