"""backend/speech package initialization.

STT engine: FRIDAY transcribes via the browser Web Speech API (instant path)
with a server-side fallback to Groq Whisper `whisper-large-v3-turbo` (free
tier) and Google Gemini 2.5 Flash audio — see ``services/stt.py``. This
package holds the personal vocabulary correction engine that permanently
fixes STT mishearings ("No, I meant X" corrections).
"""

from .personal_vocabulary import PersonalVocabularyEngine

__all__ = [
    "PersonalVocabularyEngine",
]
