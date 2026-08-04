"""backend/speech package initialization.

Only the personal vocabulary engine remains — the STT provider layer
(OpenAI / faster-whisper) was removed as dead code; FRIDAY transcribes via
the browser Web Speech API and backend/services/stt-style Gemini fallback.
"""

from .personal_vocabulary import PersonalVocabularyEngine

__all__ = [
    "PersonalVocabularyEngine",
]
