"""
settings.py — STT Subsystem configuration and environment preferences.
"""

import os
from pathlib import Path

# Speech Engine Modes: 'smart', 'openai', 'faster_whisper'
DEFAULT_PROVIDER_MODE = os.getenv("STT_PROVIDER_MODE", "smart")

# Whisper Models: 'tiny', 'base', 'small', 'medium', 'large-v3'
DEFAULT_WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Confidence threshold below which Smart Router triggers automatic secondary provider fallback
CONFIDENCE_THRESHOLD = float(os.getenv("STT_CONFIDENCE_THRESHOLD", "0.75"))

# Timeout for cloud API providers in seconds
API_TIMEOUT_SECONDS = int(os.getenv("STT_API_TIMEOUT", "10"))

# Force completely offline mode
OFFLINE_MODE = os.getenv("STT_OFFLINE_MODE", "false").lower() in ("true", "1", "yes")

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
