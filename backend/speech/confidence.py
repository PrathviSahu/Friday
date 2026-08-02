"""
confidence.py — Analyzes STT transcript confidence and latency metrics.
"""

from typing import Dict, Any
from .settings import CONFIDENCE_THRESHOLD

def evaluate_confidence(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates whether a transcription result meets quality thresholds.
    Returns result object augmented with 'is_reliable' flag.
    """
    confidence = result.get("confidence", 0.0)
    transcript = result.get("transcript", "").strip()
    error = result.get("error")

    # Unreliable if transcript is empty, had an error, or confidence is below threshold
    is_reliable = bool(transcript) and not error and (confidence >= CONFIDENCE_THRESHOLD)

    evaluated = dict(result)
    evaluated["is_reliable"] = is_reliable
    return evaluated
