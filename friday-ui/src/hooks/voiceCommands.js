export function normalizeTranscript(value = '') {
  let text = String(value)
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  
  // Strip leading and trailing wake words and filler words
  text = text
    .replace(/^(?:hey|ok|okay|hi|hello)?\s*friday\b\s*/gi, '')
    .replace(/\s*\bfriday\b$/gi, '')
    .replace(/^(?:please|could you|can you)\s+/gi, '')
    .trim();
    
  return text;
}


export function matchVoiceCommand(transcript) {
  const text = normalizeTranscript(transcript);
  console.log('[Voice] Transcript:', transcript, '-> normalized:', text);
  if (!text) return null;

  // STRICT SHORTCUT COMMAND PATTERNS
  // Require explicit action verbs (e.g. "open trading", "lock yourself") so general questions are passed to AI brain

  // ── Stop / quiet ────────────────────────────────────────────────────────
  if (/\b(?:stop|shut\s*up|quiet|hush|mute|baat\s*band)\b/.test(text)) { return 'stop'; }

  // ── Time / date ─────────────────────────────────────────────────────────
  if (/\b(?:what|kya)\s+(?:time|samay|waqt)\b/.test(text) || /^time\s*(?:now|please)?$/i.test(text)) { return 'time'; }
  if (/\b(?:what|kya)\s+(?:date|din|tarikh)\b/.test(text) || /\b(?:today|aaj)\b/.test(text)) { return 'date'; }

  // ── What's playing ──────────────────────────────────────────────────────
  if (/\b(?:what|kaun\s*sa|konsa)\s+(?:song|track|gaana|music)\b/.test(text)) { return 'what_playing'; }
  if (/\b(?:what(?:'s| is)|kya)\s+(?:playing|chal\s*raha|baj\s*raha)\b/.test(text)) { return 'what_playing'; }

  // ── Workspace / navigation (Checked BEFORE generic open app) ───────────────
  if (/\b(?:career|job\s*portal|portal|jobs|job\s*board|opportunities|career\s*os|dashboard|status)\b/.test(text)) { return 'career'; }
  if (/\b(?:lock|lockdown|secure)\b/.test(text)) { return 'lock'; }
  if (/\b(?:trading|chart|charts|workstation|trade)\b/.test(text)) { return 'trading'; }
  if (/\b(?:exit|leave|unlocked|go back)\b/.test(text)) { return 'unlocked'; }
  if (/\b(?:engineering|tech|code)\b/.test(text)) { return 'engineering'; }
  if (/\b(?:vscode|vs code|visual studio)\b/.test(text)) { return 'vscode'; }
  if (/\b(?:browser|chrome|web)\b/.test(text)) { return 'browser'; }

  // ── Open app ────────────────────────────────────────────────────────────
  const openMatch = text.match(/\b(?:open|launch|start|chalu|kholo)\s+(.+)$/);
  if (openMatch) {
    const app = openMatch[1].trim();
    const appMap = {
      'chrome': 'Google Chrome', 'brave': 'Brave Browser', 'safari': 'Safari',
      'finder': 'Finder', 'terminal': 'Terminal', 'vscode': 'Visual Studio Code',
      'vs code': 'Visual Studio Code', 'spotify': 'Spotify', 'discord': 'Discord',
      'slack': 'Slack', 'notion': 'Notion', 'figma': 'Figma', 'obsidian': 'Obsidian',
      'cursor': 'Cursor', 'arc': 'Arc',
    };
    const resolved = appMap[app] || app;
    return { type: 'open_app', app: resolved };
  }

  // ── Close app ───────────────────────────────────────────────────────────
  const closeMatch = text.match(/\b(?:close|quit|band|exit)\s+(.+)$/);
  if (closeMatch) {
    const app = closeMatch[1].trim();
    return { type: 'close_app', app };
  }

  return null;
}


export function shouldVerifyVoice(confidence = 0) {
  return Number(confidence) >= 0.7;
}