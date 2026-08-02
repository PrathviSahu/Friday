"""
transcript_cleaner.py — Sanitizes raw transcripts before intent parsing.
Strips leading/trailing wake words ("Friday", "Hey Friday"), filler phrases, and normalizes capitalization.
"""

import re

WAKE_WORDS_PATTERN = re.compile(
    r'^(?:hey|ok|okay|hi|hello)?\s*friday\b\s*|'
    r'\s*\bfriday\b$|'
    r'^(?:please|could you|can you|would you)\s+',
    re.IGNORECASE
)

FILLER_WORDS_PATTERN = re.compile(
    r'\b(?:um|uh|ah|like|you know)\b',
    re.IGNORECASE
)

def clean_transcript(raw_text: str) -> str:
    """Cleans and sanitizes raw STT transcripts."""
    if not raw_text or not isinstance(raw_text, str):
        return ""

    # Strip wake words and leading fillers
    text = WAKE_WORDS_PATTERN.sub('', raw_text.strip()).strip()
    # Strip secondary trailing wake words
    text = re.sub(r'(?i)\bfriday\b$', '', text).strip()
    # Remove verbal hesitation fillers
    text = FILLER_WORDS_PATTERN.sub('', text).strip()
    # Normalize multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    # Capitalize first letter cleanly
    if text:
        text = text[0].upper() + text[1:]

    return text
