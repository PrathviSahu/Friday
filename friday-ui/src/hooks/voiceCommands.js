export function normalizeTranscript(value = '') {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}


export function matchVoiceCommand(transcript) {
  const text = normalizeTranscript(transcript);
  console.log('[Voice] Transcript:', transcript, '-> normalized:', text);
  if (!text) return null;

  // STRICT SHORTCUT COMMAND PATTERNS
  // Require explicit action verbs (e.g. "open trading", "lock yourself") so general questions are passed to AI brain
  if (/\b(?:lock|lockdown|secure)\b/.test(text)) { return 'lock'; }
  if (/\b(?:trading|chart|charts|workstation|trade)\b/.test(text)) { return 'trading'; }
  if (/\b(?:exit|leave|unlocked|go back)\b/.test(text)) { return 'unlocked'; }
  if (/\b(?:engineering|tech|code)\b/.test(text)) { return 'engineering'; }
  if (/\b(?:vscode|vs code|visual studio)\b/.test(text)) { return 'vscode'; }
  if (/\b(?:browser|chrome|web)\b/.test(text)) { return 'browser'; }
  if (/\b(?:dashboard|status)\b/.test(text)) { return 'dashboard'; }

  return null;
}


export function shouldVerifyVoice(confidence = 0) {
  return Number(confidence) >= 0.7;
}