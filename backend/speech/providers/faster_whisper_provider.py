"""
faster_whisper_provider.py — Local offline Whisper provider using faster-whisper or whisper fallback.
Models ('tiny', 'base', 'small', 'medium', 'large-v3') are loaded lazily ONCE and kept warm.
"""

import time
import logging
from typing import Dict, Any, Union, Optional
from pathlib import Path
from .base_provider import BaseSTTProvider
from ..settings import DEFAULT_WHISPER_MODEL

logger = logging.getLogger("friday_whisper")

class FasterWhisperProvider(BaseSTTProvider):
    _shared_model = None
    _loaded_model_name = None

    def __init__(self, model_name: str = None):
        self.model_name = model_name or DEFAULT_WHISPER_MODEL

    def initialize(self) -> bool:
        if FasterWhisperProvider._shared_model and FasterWhisperProvider._loaded_model_name == self.model_name:
            return True

        try:
            # Try loading faster_whisper first
            try:
                from faster_whisper import WhisperModel
                FasterWhisperProvider._shared_model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
                FasterWhisperProvider._loaded_model_name = self.model_name
                logger.info(f"[FasterWhisper] Loaded faster-whisper model '{self.model_name}'")
                return True
            except ImportError:
                # Fallback to standard whisper if available
                import whisper
                FasterWhisperProvider._shared_model = whisper.load_model(self.model_name)
                FasterWhisperProvider._loaded_model_name = self.model_name
                logger.info(f"[Whisper] Loaded standard whisper model '{self.model_name}'")
                return True
        except Exception as err:
            logger.warning(f"[FasterWhisper] Could not load model '{self.model_name}': {err}")
            return False

    @property
    def provider_name(self) -> str:
        return f"faster_whisper_{self.model_name}"

    def available(self) -> bool:
        return True  # Local fallback is always available

    def health_check(self) -> bool:
        return self.initialize()

    def transcribe(self, audio_source: Union[str, Path, bytes]) -> Dict[str, Any]:
        start_time = time.time()
        
        if not self.initialize():
            return {
                "transcript": "",
                "confidence": 0.0,
                "latency": time.time() - start_time,
                "provider": self.provider_name,
                "error": "FasterWhisper model unavailable"
            }

        try:
            file_path = str(audio_source)
            model = FasterWhisperProvider._shared_model
            
            # Check model type (faster_whisper vs standard whisper)
            if hasattr(model, "transcribe"):
                res = model.transcribe(file_path)
                if isinstance(res, tuple):
                    # faster_whisper returns (segments_generator, info)
                    segments, info = res
                    text_parts = [segment.text for segment in segments]
                    transcript = " ".join(text_parts).strip()
                    avg_prob = getattr(info, "avg_logprob", 0.0)
                    confidence = max(0.1, min(0.99, 1.0 + (avg_prob / 5.0))) if transcript else 0.0
                else:
                    # standard whisper dictionary
                    transcript = res.get("text", "").strip()
                    confidence = 0.88 if transcript else 0.0
            else:
                transcript = ""
                confidence = 0.0

            latency = time.time() - start_time
            return {
                "transcript": transcript,
                "confidence": round(confidence, 2),
                "latency": round(latency, 3),
                "provider": self.provider_name,
                "error": None
            }

        except Exception as err:
            return {
                "transcript": "",
                "confidence": 0.0,
                "latency": round(time.time() - start_time, 3),
                "provider": self.provider_name,
                "error": str(err)
            }
