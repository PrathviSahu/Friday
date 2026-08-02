"""
personality_engine.py — Formats and polishes F.R.I.D.A.Y.'s spoken and textual responses.
Enforces the authentic British female AI persona (authoritative, witty, concise, addressing user as "Boss" or "Prem").
"""

import re

FRIDAY_SYSTEM_PROMPT = """You are F.R.I.D.A.Y., a highly advanced, authoritative, and sharp British AI companion created for Boss (Prem).
Tone Rules:
1. Address the user naturally as 'Boss' or 'Prem'.
2. Be direct, witty, and concise. Avoid wordy intros or robotic disclaimers.
3. Spoken output must be natural and ready for Edge-TTS (en-GB-SoniaNeural).
4. Never break character. You manage Career OS, Trading Workstation, System Telemetry, and desktop tasks smoothly.
"""

def format_speech_output(text: str) -> str:
    """Polishes raw LLM responses for natural British speech output."""
    if not text:
        return "Standing by, Boss."
    
    # Remove markdown codeblocks or heavy formatting from TTS stream
    clean = re.sub(r'```[\s\S]*?```', '', text)
    clean = re.sub(r'[*_#`]', '', clean)
    clean = clean.strip()
    
    # Ensure natural ending punctuation
    if clean and not clean[-1] in '.!?':
        clean += '.'
        
    return clean
