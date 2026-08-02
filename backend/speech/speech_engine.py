"""
speech_engine.py — High-Level Speech Engine Façade.
The main application interface for Speech-to-Text processing.
Decouples UI, Brain, and Planner from underlying STT providers, cleaning, and memory corrections.
"""

from typing import Dict, Any, Union
from pathlib import Path
from .router import STTRouter
from .transcript_cleaner import clean_transcript
from .personal_vocabulary import PersonalVocabularyEngine

class SpeechEngine:
    def __init__(self, mode: str = None):
        self.router = STTRouter(mode=mode)
        self.vocab_engine = PersonalVocabularyEngine()

    def process_audio(self, audio_source: Union[str, Path, bytes]) -> Dict[str, Any]:
        """
        Full STT Pipeline:
        1. STT Router Transcribes Audio (OpenAI / FasterWhisper / Fallback)
        2. Clean Transcript (Strips wake words, fillers, whitespace)
        3. Apply Personal Vocabulary & Learned Corrections
        """
        # 1. Route transcription
        stt_result = self.router.route_transcription(audio_source)
        raw_transcript = stt_result.get("transcript", "")

        # 2. Clean wake words & fillers
        cleaned = clean_transcript(raw_transcript)

        # 3. Apply personal learned corrections
        final_transcript = self.vocab_engine.apply_corrections(cleaned)

        return {
            "transcript": final_transcript,
            "raw_transcript": raw_transcript,
            "confidence": stt_result.get("confidence", 0.0),
            "provider": stt_result.get("provider", "unknown"),
            "latency": stt_result.get("latency", 0.0),
            "fallback_triggered": stt_result.get("fallback_triggered", False),
            "error": stt_result.get("error")
        }

# Global Singleton Instance
speech_engine = SpeechEngine()
