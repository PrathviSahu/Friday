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

  // LOCK SYSTEM PATTERNS
  if (/\b(?:lock|secure|lock yourself|lock down|lock system)\b/.test(text)) { return 'lock'; }

  // COMMAND PATTERNS
  if (/\btrading\b/.test(text)) { return 'trading'; }
  if (/\bengineering\b/.test(text)) { return 'engineering'; }
  if (/\b(?:open|launch|start)\b.*\b(?:vscode|visual studio code|vs code|code)\b/.test(text)) { return 'vscode'; }
  if (/\b(?:open|launch|start)\b.*\b(?:browser|chrome|edge|safari)\b/.test(text)) { return 'browser'; }
  if (/\b(?:open|show|launch)\b.*\b(?:dashboard|status|panel)\b/.test(text)) { return 'dashboard'; }

  return null;
}


export function shouldVerifyVoice(confidence = 0) {
  return Number(confidence) >= 0.7;
}