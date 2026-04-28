"""
language_detector.py

Detects language for each section during chunking.

Phase 1 already provides a document-level language_hint,
but tenders can contain mixed languages (English + Hindi etc).

This module detects language at the section level.
"""

from langdetect import detect


def detect_language(text: str, fallback: str = "en") -> str:
    """
    Detect language from section text.

    Args:
        text: section content
        fallback: language to return if detection fails

    Returns:
        ISO language code (en, hi, fr, etc)
    """

    if not text or len(text.strip()) < 30:
        return fallback

    try:
        return detect(text[:1000])
    except Exception:
        return fallback