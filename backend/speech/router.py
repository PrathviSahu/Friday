"""
router.py — STT Provider Router & Fallback Orchestrator.
Manages provider selection ('smart', 'openai', 'faster_whisper') and automatic seamless failovers.
"""

import logging
from typing import Dict, Any, Union, List
from pathlib import Path
from .providers.base_provider import BaseSTTProvider
from .providers.openai_provider import OpenAIProvider
from .providers.faster_whisper_provider import FasterWhisperProvider
from .confidence import evaluate_confidence
from .settings import DEFAULT_PROVIDER_MODE, OFFLINE_MODE

logger = logging.getLogger("friday_stt_router")

class STTRouter:
    def __init__(self, mode: str = None):
        self.mode = mode or DEFAULT_PROVIDER_MODE
        self.providers: Dict[str, BaseSTTProvider] = {
            "openai": OpenAIProvider(),
            "faster_whisper": FasterWhisperProvider()
        }

    def route_transcription(self, audio_source: Union[str, Path, bytes]) -> Dict[str, Any]:
        """Routes audio through selected or smart fallback STT providers."""
        
        # Force offline mode if configured
        if OFFLINE_MODE:
            logger.info("[STT Router] Forced offline mode — using FasterWhisper")
            return self._transcribe_with_provider("faster_whisper", audio_source)

        if self.mode == "openai":
            res = self._transcribe_with_provider("openai", audio_source)
            if not res.get("error"):
                return res
            # Failover to local if OpenAI explicitly failed
            logger.warning(f"[STT Router] OpenAI failed ({res.get('error')}) — falling back to FasterWhisper")
            return self._transcribe_with_provider("faster_whisper", audio_source, fallback=True)

        elif self.mode == "faster_whisper":
            return self._transcribe_with_provider("faster_whisper", audio_source)

        # Smart Mode (Default): OpenAI first -> fallback to FasterWhisper if unavailable or low confidence
        else:
            openai = self.providers["openai"]
            if openai.available():
                logger.info("[STT Router] Smart Mode: Trying OpenAI Provider...")
                res = self._transcribe_with_provider("openai", audio_source)
                eval_res = evaluate_confidence(res)

                if eval_res.get("is_reliable"):
                    return res

                logger.warning(f"[STT Router] OpenAI returned low confidence/error ({res.get('error')}) — triggering fallback to FasterWhisper")
            
            # Local FasterWhisper Fallback
            logger.info("[STT Router] Routing to FasterWhisper Provider...")
            fallback_res = self._transcribe_with_provider("faster_whisper", audio_source, fallback=True)
            return fallback_res

    def _transcribe_with_provider(self, provider_key: str, audio_source: Union[str, Path, bytes], fallback: bool = False) -> Dict[str, Any]:
        provider = self.providers.get(provider_key)
        if not provider:
            return {
                "transcript": "",
                "confidence": 0.0,
                "latency": 0.0,
                "provider": "none",
                "error": f"Provider '{provider_key}' not registered"
            }

        res = provider.transcribe(audio_source)
        res["fallback_triggered"] = fallback
        return res
