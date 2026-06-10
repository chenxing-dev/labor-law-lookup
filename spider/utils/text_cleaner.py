"""
文本清洗 helper functions
"""
import re


def normalize_text(text: str) -> str:
    """Normalize text by removing extra whitespace and trimming."""
    return re.sub(r"\s+", " ", (text or "")).strip()
