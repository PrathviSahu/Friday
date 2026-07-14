import re

# Simple response formatter to apply F.R.I.D.A.Y. personality rules.
# Keeps transformations small and deterministic so production-ready.

COMMAND_MAP = {
    r'^(open|launch) (visual studio code|vscode)': 'Certainly, Boss. Opening Visual Studio Code.',
    r'^(open|launch) (browser|the browser)': 'Certainly, Boss. Opening your browser.',
    r'^(open|show|display) (dashboard|the dashboard)': 'Certainly, Boss. Displaying the dashboard.',
    r'^(lock|secure|lock system|secure system)': 'Security mode activated.',
    r'^(wake|wake word|yes boss\?|yes boss)': 'Yes, Boss?',
}

UNKNOWN_REPLY = "I'm afraid I didn't understand that, Boss."

def format_response(text: str) -> str:
    if not text or not isinstance(text, str):
        return UNKNOWN_REPLY

    t = text.strip()
    low = t.lower()

    # Command mappings
    for pattern, reply in COMMAND_MAP.items():
        if re.search(pattern, low):
            return reply

    # Stock/price pattern: "The current Tesla stock price is $X" -> "Tesla is currently trading at $X."
    m = re.search(r'the current\s+([A-Za-z0-9\.\s]+?)\s+stock price is\s+(.*)', low)
    if m:
        name = m.group(1).strip().title()
        rest = m.group(2).strip()
        return f"{name} is currently trading at {rest}."

    # Politeness and phrasing adjustments
    # Shorten "Sure, I'll <do it>" to "Certainly, Boss. <Doing it>"
    m2 = re.match(r'^(sure|okay|ok)[,\s]+i(?:\'|’)ll\s+(.*)', low)
    if m2:
        action = m2.group(2).strip().capitalize()
        return f"Certainly, Boss. {action}."

    # If it begins with a verb phrase, make it concise and address Boss
    if re.match(r'^(open|show|display|start|stop|lock|unlock|activate|deactivate|enable|disable)\b', low):
        sentence = t[0].upper() + t[1:]
        return f"Certainly, Boss. {sentence}"

    # Default: ensure not verbose and address the user as 'Boss'
    # Take first sentence (split on .!?), keep it short
    first_sentence = re.split(r'[\.\!?]\s', t)[0]
    first_sentence = first_sentence.strip()
    if len(first_sentence) == 0:
        return UNKNOWN_REPLY
    # Capitalize properly
    cap = first_sentence[0].upper() + first_sentence[1:]
    if 'boss' not in cap.lower():
        cap = f"{cap}."
        return f"{cap}"
    return cap
