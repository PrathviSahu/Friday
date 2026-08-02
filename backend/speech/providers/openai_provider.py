"""
openai_provider.py — OpenAI Whisper API provider.
Communicates with OpenAI audio transcription API with latency and confidence metrics.
"""

import time
import os
import urllib.request
import urllib.parse
import json
from typing import Dict, Any, Union
from pathlib import Path
from .base_provider import BaseSTTProvider
from ..settings import API_TIMEOUT_SECONDS

class OpenAIProvider(BaseSTTProvider):
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()

    def initialize(self) -> bool:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    def available(self) -> bool:
        return bool(self.api_key)

    def health_check(self) -> bool:
        return self.available()

    def transcribe(self, audio_source: Union[str, Path, bytes]) -> Dict[str, Any]:
        start_time = time.time()
        if not self.available():
            return {
                "transcript": "",
                "confidence": 0.0,
                "latency": time.time() - start_time,
                "provider": self.provider_name,
                "error": "OpenAI API key missing"
            }

        try:
            # Multi-part form audio submission
            file_path = Path(audio_source) if isinstance(audio_source, (str, Path)) else None
            if not file_path or not file_path.exists():
                return {
                    "transcript": "",
                    "confidence": 0.0,
                    "latency": time.time() - start_time,
                    "provider": self.provider_name,
                    "error": "Audio file not found"
                }

            # Boundary setup for multipart/form-data
            boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
            body = []
            
            # Model field
            body.append(f'--{boundary}'.encode())
            body.append(b'Content-Disposition: form-data; name="model"')
            body.append(b'')
            body.append(b'whisper-1')

            # Audio file field
            body.append(f'--{boundary}'.encode())
            body.append(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"'.encode())
            body.append(b'Content-Type: audio/mpeg')
            body.append(b'')
            body.append(file_path.read_bytes())
            
            body.append(f'--{boundary}--'.encode())
            body.append(b'')
            
            payload = b'\r\n'.join(body)

            req = urllib.request.Request(
                "https://api.openai.com/v1/audio/transcriptions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as resp:
                res = json.loads(resp.read().decode())
                transcript = res.get("text", "").strip()

            latency = time.time() - start_time
            # High baseline confidence for OpenAI API
            confidence = 0.95 if transcript else 0.0

            return {
                "transcript": transcript,
                "confidence": confidence,
                "latency": latency,
                "provider": self.provider_name,
                "error": None
            }

        except Exception as err:
            return {
                "transcript": "",
                "confidence": 0.0,
                "latency": time.time() - start_time,
                "provider": self.provider_name,
                "error": str(err)
            }
