"""
base_provider.py — Abstract base class for all STT providers.
Enforces SOLID contract across OpenAI, Faster-Whisper, and future cloud/local STT providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Union
from pathlib import Path

class BaseSTTProvider(ABC):
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initializes the provider, loading local models or checking API connections."""
        pass

    @abstractmethod
    def transcribe(self, audio_source: Union[str, Path, bytes]) -> Dict[str, Any]:
        """
        Transcribes audio source into a structured dictionary.
        Returns:
            {
                "transcript": str,
                "confidence": float,  # 0.0 to 1.0
                "latency": float,     # seconds
                "provider": str,
                "error": Optional[str]
            }
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Returns True if the provider is operational."""
        pass

    @abstractmethod
    def available(self) -> bool:
        """Returns True if required models/keys are present."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        pass
