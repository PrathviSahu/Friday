import { API_ENDPOINTS, resolveApiUrl } from '../api/config.js';

let currentAudio = null;
let currentResolve = null; // Holds the pending speak() promise resolver for instant abort
let duckTts = false;       // when true, TTS volume is lowered so the mic can hear the user
let speechSeq = 0;         // Monotonic sequence ID ensuring strict single-speech exclusivity

/**
 * Lower/restore FRIDAY's own TTS volume. Whisper-mode VAD uses this so her
 * own voice doesn't trigger barge-in — the user's voice is louder by
 * comparison, so a voice onset while ducked is reliably the user.
 */
export function setTtsDucking(on) {
  duckTts = !!on;
  if (currentAudio) {
    try { currentAudio.volume = duckTts ? 0.35 : 1; } catch (_) {}
  }
}

/**
 * Instantly stop any currently playing audio and resolve the pending speak() promise,
 * so the await speak(...) in useSpeech.js returns immediately.
 */
export function stopSpeaking() {
  speechSeq += 1; // Invalidate any in-flight async TTS fetches or callbacks
  fetch(`${API_ENDPOINTS.spotify}/unduck`, { method: 'POST' }).catch(() => {});

  if (currentResolve) {
    const resolve = currentResolve;
    currentResolve = null;
    try { resolve(); } catch (_) {}
  }

  if (currentAudio) {
    try {
      currentAudio.pause();
      currentAudio.currentTime = 0;
    } catch (_) {}
    currentAudio = null;
  }

  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
    } catch (_) {}
  }
}

export async function speak(text) {
  if (!text || typeof text !== 'string') return;
  const clean = text.trim();
  if (!clean) return;

  // Kill ANY ongoing audio/speech instantly before starting a new one
  stopSpeaking();
  const mySeq = speechSeq;

  fetch(`${API_ENDPOINTS.spotify}/duck`, { method: 'POST' }).catch(() => {});
  const doneSpeaking = () => {
    fetch(`${API_ENDPOINTS.spotify}/unduck`, { method: 'POST' }).catch(() => {});
  };

  try {
    const response = await fetch(API_ENDPOINTS.tts, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: clean }),
    });

    // Check if another speak() or stopSpeaking() was called while fetching
    if (mySeq !== speechSeq) return;

    if (response.ok) {
      const data = await response.json();
      if (mySeq !== speechSeq) return;

      if (data.audio_url) {
        return new Promise((resolve) => {
          currentResolve = resolve;
          const audio = new Audio(resolveApiUrl(data.audio_url));
          currentAudio = audio;
          audio.volume = duckTts ? 0.35 : 1;

          const finish = () => {
            if (currentAudio === audio) currentAudio = null;
            doneSpeaking();
            if (currentResolve === resolve) {
              currentResolve = null;
              resolve();
            }
          };

          audio.onended = finish;
          audio.onerror = () => {
            if (mySeq !== speechSeq) return;
            if (currentAudio === audio) currentAudio = null;
            fallbackWebSpeech(clean, mySeq, () => {
              doneSpeaking();
              if (currentResolve === resolve) {
                currentResolve = null;
                resolve();
              }
            });
          };

          audio.play().catch(() => {
            if (mySeq !== speechSeq) return;
            if (currentAudio === audio) currentAudio = null;
            fallbackWebSpeech(clean, mySeq, () => {
              doneSpeaking();
              if (currentResolve === resolve) {
                currentResolve = null;
                resolve();
              }
            });
          });
        });
      }
    }
  } catch (err) {
    console.warn('[TTS] Backend TTS error, using fallback:', err);
  }

  if (mySeq !== speechSeq) return;

  return new Promise((resolve) => {
    currentResolve = resolve;
    fallbackWebSpeech(clean, mySeq, () => {
      doneSpeaking();
      if (currentResolve === resolve) {
        currentResolve = null;
        resolve();
      }
    });
  });
}

function fallbackWebSpeech(text, expectedSeq, onEnd) {
  if (expectedSeq !== undefined && expectedSeq !== speechSeq) {
    if (onEnd) onEnd();
    return;
  }
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    if (onEnd) onEnd();
    return;
  }

  try {
    window.speechSynthesis.cancel();
  } catch (_) {}

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.pitch = 1.0;
  utterance.rate = 1.0;
  utterance.volume = duckTts ? 0.35 : 1;

  const voices = window.speechSynthesis.getVoices() || [];
  const preferredVoice = voices.find(v => {
    const lang = (v.lang || '').toLowerCase();
    const name = (v.name || '').toLowerCase();
    return lang.includes('en-in') || name.includes('neerja') || name.includes('swara') || name.includes('rishi');
  }) || voices.find(v => (v.lang || '').toLowerCase().startsWith('en'));

  if (preferredVoice) utterance.voice = preferredVoice;

  utterance.onend = () => {
    if (onEnd) onEnd();
  };
  utterance.onerror = () => {
    if (onEnd) onEnd();
  };

  try {
    window.speechSynthesis.speak(utterance);
  } catch (_) {
    if (onEnd) onEnd();
  }
}
