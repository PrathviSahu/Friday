"""services/brain/clients.py — LLM API client singletons & JSON parser."""

import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend/.env environment variables are loaded
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from groq import Groq
from google import genai

_groq_client = None
_gemini_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key != "your_key_here":
            _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = brace.group(0) if brace else None
    if not candidate:
        return {}
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {}
