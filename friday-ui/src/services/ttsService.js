import { API_ENDPOINTS, resolveApiUrl } from '../api/config.js';

let currentAudio = null;
let currentResolve = null; // Holds the pending speak() promise resolver for instant abort
let duckTts = false;       // when true, TTS volume is lowered so the mic can hear the user
let speechSeq = 0;         // Monotonic sequence ID ensuring strict single-speech exclusivity
let isMobileAudioUnlocked = false;
let cachedVoices = [];

// ── Mobile Speech & Audio Autoplay Unlocker ────────────────────────────────
// iOS Safari & Mobile Chrome require speech/audio to be unlocked during a user gesture.
export function unlockMobileAudio() {
  if (isMobileAudioUnlocked || typeof window === 'undefined') return;
  isMobileAudioUnlocked = true;

  try {
    // 1. Prime Web Speech Synthesis
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const silentUtterance = new SpeechSynthesisUtterance(' ');
      silentUtterance.volume = 0.01;
      silentUtterance.rate = 2.0;
      window.speechSynthesis.speak(silentUtterance);
    }
  } catch (_) {}

  try {
    // 2. Prime HTML5 Audio Context
    const silentAudio = new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA');
    silentAudio.volume = 0.01;
    const playPromise = silentAudio.play();
    if (playPromise !== undefined) {
      playPromise.then(() => silentAudio.pause()).catch(() => {});
    }
  } catch (_) {}
}

// Auto-register unlock listener on first touch/click
if (typeof window !== 'undefined') {
  const unlockEvents = ['touchstart', 'touchend', 'pointerdown', 'click', 'keydown'];
  const handleFirstInteraction = () => {
    unlockMobileAudio();
    unlockEvents.forEach(evt => window.removeEventListener(evt, handleFirstInteraction));
  };
  unlockEvents.forEach(evt => window.addEventListener(evt, handleFirstInteraction, { passive: true, once: true }));

  // Pre-cache available voices
  if ('speechSynthesis' in window) {
    const updateVoices = () => {
      try {
        cachedVoices = window.speechSynthesis.getVoices() || [];
      } catch (_) {}
    };
    updateVoices();
    window.speechSynthesis.onvoiceschanged = updateVoices;
  }
}

/**
 * Lower/restore FRIDAY's own TTS volume. Whisper-mode VAD uses this so her
 * own voice doesn't trigger barge-in.
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

  // Make sure mobile audio permissions are primed
  unlockMobileAudio();

  // Kill ANY ongoing audio/speech instantly before starting a new one
  stopSpeaking();
  const mySeq = speechSeq;

  fetch(`${API_ENDPOINTS.spotify}/duck`, { method: 'POST' }).catch(() => {});
  const doneSpeaking = () => {
    fetch(`${API_ENDPOINTS.spotify}/unduck`, { method: 'POST' }).catch(() => {});
  };

  // ⚡ Low-Latency Neural Audio Streaming (Sub-200ms TTFA with Memory Cache)
  try {
    const streamUrl = `${API_ENDPOINTS.ttsStream || `${API_ENDPOINTS.tts}/stream`}?text=${encodeURIComponent(clean)}`;
    
    return await new Promise((resolve) => {
      currentResolve = resolve;
      const audio = new Audio(resolveApiUrl(streamUrl));
      currentAudio = audio;
      audio.volume = duckTts ? 0.35 : 1;

      let hasEnded = false;
      const finish = () => {
        if (hasEnded) return;
        hasEnded = true;
        if (currentAudio === audio) currentAudio = null;
        doneSpeaking();
        if (currentResolve === resolve) {
          currentResolve = null;
          resolve();
        }
      };

      audio.onended = finish;

      const triggerFallback = () => {
        if (hasEnded || mySeq !== speechSeq) return;
        hasEnded = true;
        if (currentAudio === audio) currentAudio = null;
        fallbackWebSpeech(clean, mySeq, () => {
          doneSpeaking();
          if (currentResolve === resolve) {
            currentResolve = null;
            resolve();
          }
        });
      };

      audio.onerror = () => {
        triggerFallback();
      };

      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          triggerFallback();
        });
      }
    });
  } catch (err) {
    console.warn('[TTS] Streaming TTS error, falling back to WebSpeech:', err);
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
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }
  } catch (_) {}

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.pitch = 1.05;
  utterance.rate = 1.0;
  utterance.volume = duckTts ? 0.35 : 1;

  // Keep global reference on window to prevent iOS Safari GC bug
  window._fridayActiveUtterance = utterance;

  const voices = cachedVoices.length > 0 ? cachedVoices : (window.speechSynthesis.getVoices() || []);
  const preferredVoice = voices.find(v => {
    const lang = (v.lang || '').toLowerCase();
    const name = (v.name || '').toLowerCase();
    return (
      name.includes('samantha') ||
      name.includes('siri') ||
      name.includes('neerja') ||
      name.includes('swara') ||
      name.includes('karen') ||
      name.includes('moira') ||
      lang.includes('en-in') ||
      lang.includes('en-gb') ||
      lang.includes('en-us')
    );
  }) || voices.find(v => (v.lang || '').toLowerCase().startsWith('en'));

  if (preferredVoice) utterance.voice = preferredVoice;

  let hasEnded = false;
  const safeEnd = () => {
    if (hasEnded) return;
    hasEnded = true;
    window._fridayActiveUtterance = null;
    if (onEnd) onEnd();
  };

  utterance.onend = safeEnd;
  utterance.onerror = safeEnd;

  // Maximum speech watchdog timeout (12s) to prevent any mobile browser deadlock
  setTimeout(() => {
    if (!hasEnded && expectedSeq === speechSeq) {
      safeEnd();
    }
  }, Math.max(4000, Math.min(15000, text.length * 100)));

  try {
    window.speechSynthesis.speak(utterance);
    // Kick resume for iOS WebKit
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }
  } catch (_) {
    safeEnd();
  }
}
