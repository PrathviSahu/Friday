import { API_ENDPOINTS, resolveApiUrl } from '../api/config.js';

let currentAudio = null;
let currentResolve = null; // Holds the pending speak() promise resolver for instant abort
let duckTts = false;       // when true, TTS volume is lowered so the mic can hear the user

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
  // Restore Spotify volume immediately on interrupt
  fetch(`${API_ENDPOINTS.spotify}/unduck`, { method: 'POST' }).catch(() => {});

  // Resolve pending promise immediately so await speak() returns and loop continues
  if (currentResolve) {
    const resolve = currentResolve;
    currentResolve = null;
    resolve();
    console.log('[TTS] Speech interrupted — stopped mid-sentence.');
  }

  // Hard-stop browser audio element
  if (currentAudio) {
    try {
      currentAudio.pause();
      currentAudio.currentTime = 0;
    } catch (_) {}
    currentAudio = null;
  }

  // Cancel Web Speech API fallback
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
}

export async function speak(text) {
  if (!text || typeof text !== 'string') return;

  // Duck Spotify music volume while FRIDAY is speaking
  fetch(`${API_ENDPOINTS.spotify}/duck`, { method: 'POST' }).catch(() => {});

  const doneSpeaking = () => {
    fetch(`${API_ENDPOINTS.spotify}/unduck`, { method: 'POST' }).catch(() => {});
  };

  // Only stop a PREVIOUS audio if something is actively playing
  if (currentAudio) {
    try { currentAudio.pause(); currentAudio.currentTime = 0; } catch (_) {}
    currentAudio = null;
  }

  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }

  try {
    const response = await fetch(API_ENDPOINTS.tts, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });

    if (response.ok) {
      const data = await response.json();
      if (data.audio_url) {
        return new Promise((resolve) => {
          // Store resolver so stopSpeaking() can resolve this promise instantly from outside
          currentResolve = resolve;

          // Backend returns a relative path (/temp_audio/...); resolve against
          // the configured API base so it works via the dev proxy or a
          // production VITE_API_URL alike.
          const audio = new Audio(resolveApiUrl(data.audio_url));
          currentAudio = audio;
          audio.volume = duckTts ? 0.35 : 1;

          audio.onended = () => {
            currentAudio = null;
            doneSpeaking();
            if (currentResolve === resolve) {
              currentResolve = null;
              resolve();
            }
          };

          audio.onerror = () => {
            currentAudio = null;
            if (currentResolve === resolve) {
              currentResolve = null;
            }
            fallbackWebSpeech(text, () => {
              doneSpeaking();
              resolve();
            });
          };

          audio.play().catch(() => {
            currentAudio = null;
            if (currentResolve === resolve) {
              currentResolve = null;
            }
            fallbackWebSpeech(text, () => {
              doneSpeaking();
              resolve();
            });
          });
        });
      }
    }
  } catch (err) {
    console.warn('[TTS] Backend TTS error, using browser fallback:', err);
  }

  return new Promise((resolve) => {
    currentResolve = resolve;
    fallbackWebSpeech(text, () => {
      doneSpeaking();
      if (currentResolve === resolve) {
        currentResolve = null;
      }
      resolve();
    });
  });

}

function fallbackWebSpeech(text, onEnd) {
  if (!('speechSynthesis' in window)) {
    if (onEnd) onEnd();
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.pitch = 1.0;
  utterance.rate = 1.0;
  utterance.volume = duckTts ? 0.35 : 1;

  const voices = window.speechSynthesis.getVoices();
  // Target Indian English voices first (en-IN, Neerja, Rishi, Veena, Swara)
  const indianVoice = voices.find(v => {
    const lang = (v.lang || '').toLowerCase();
    const name = (v.name || '').toLowerCase();
    return (lang.includes('en-in') || lang.includes('en_in') || name.includes('india') || name.includes('neerja') || name.includes('swara') || name.includes('veena') || name.includes('rishi'));
  }) || voices.find(v => {
    const lang = (v.lang || '').toLowerCase();
    const name = (v.name || '').toLowerCase();
    return !lang.includes('en-gb') && !name.includes('uk') && !name.includes('british') && !name.includes('daniel');
  });

  if (indianVoice) utterance.voice = indianVoice;

  utterance.onend = () => { if (onEnd) onEnd(); };
  utterance.onerror = () => { if (onEnd) onEnd(); };
  window.speechSynthesis.speak(utterance);
}
