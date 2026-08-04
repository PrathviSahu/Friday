import { useEffect, useRef } from 'react';
import { matchVoiceCommand } from './voiceCommands';
import { fetchChatText } from '../api/chatText';
import { transcribeAudioBlob } from '../api/speech';
import { speak, stopSpeaking, setTtsDucking } from '../services/ttsService';

const withTimeout = (promise, ms) =>
  Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`Timeout after ${ms}ms`)), ms)
    ),
  ]);

// Patterns that look like an intentional user command — used to decide
// barge-in while FRIDAY is speaking. Her own echo rarely contains these,
// so random noise / partial echoes never interrupt her.
const COMMAND_LIKE = /\b(?:hey|ok|okay|suno|aye)?\s*(?:friday|fraide|frida|freddy|frieda|freddie|freya|phiday)\b|\b(?:open|close|play|pause|next|previous|volume|mute|time|date|today|what|who|when|where|why|how|set|search|lock|unlock|trading|dashboard|career|weather|todo|song|music|gaana|chalu|band|kya|kaun|konsa|stop|quiet|hush|wait)\b/i;

export function useSpeech({ locked, isLocked, workspace = 'unlocked', enabled = true, mode = 'always', onCommand, onConversation }) {
  // Support both prop name variants: locked (LockScreen) and isLocked (legacy)
  const _locked = locked ?? isLocked ?? false;
  const activeRef         = useRef(false);  // true while a mic/recognizer is live
  const processingRef     = useRef(false);  // true while a command is being handled
  const speakingRef       = useRef(false);  // true while FRIDAY's TTS is playing
  const enabledRef        = useRef(enabled); // mirrors the enabled prop reactively
  const lockedRef         = useRef(_locked);
  const workspaceRef      = useRef(workspace);
  const onCommandRef      = useRef(onCommand);
  const onConvRef         = useRef(onConversation);
  const lastTranscriptRef = useRef(null); // { text, ts } — dedup guard for double-fired transcripts
  const lastSpokenTtsRef  = useRef({ text: '', ts: 0 }); // stores FRIDAY's own spoken text to prevent self-echo loops
  const speechGenRef      = useRef(0); // increments per TTS reply — stale replies can't clear the current speaking state

  // Listening mode: 'always' (mic always listening) or 'ptt' (hold Space to talk).
  // PTT keeps the microphone fully closed between holds — privacy-friendly.
  const listeningModeRef = useRef(mode);
  const pttSessionRef    = useRef({ active: false }); // true while Space is held

  // STT engine mode: 'browser' (Web Speech API) or 'whisper' (backend
  // Groq Whisper free tier via recorded clips). We auto-switch to 'whisper'
  // when the browser engine is unsupported or keeps failing.
  const modeRef          = useRef('browser');
  const micBlockedRef    = useRef(false); // mic permission denied — stop retrying

  // Whisper-mode resources (stream / VAD / MediaRecorder)
  const streamRef        = useRef(null);
  const audioCtxRef      = useRef(null);
  const analyserRef      = useRef(null);
  const recorderRef      = useRef(null);
  const chunksRef        = useRef([]);
  const vadRef           = useRef({ state: 'idle', speechStart: 0, lastVoice: 0, quietFrames: 0 });
  const vadFrameRef      = useRef(null);

  // Keep refs in sync with props every render — no re-mount needed
  useEffect(() => { lockedRef.current = _locked; }, [_locked]);
  useEffect(() => { workspaceRef.current = workspace; }, [workspace]);
  useEffect(() => { onCommandRef.current = onCommand; }, [onCommand]);
  useEffect(() => { onConvRef.current = onConversation; }, [onConversation]);
  useEffect(() => { listeningModeRef.current = mode; }, [mode]);

  // When enabled flips OFF → abort recognizer + whisper resources immediately.
  useEffect(() => {
    enabledRef.current = enabled;
    if (!enabled) {
      stopRecognizer();
    } else {
      // Give the user a fresh chance after granting mic permission in browser
      // settings (or toggling the mic off/on).
      micBlockedRef.current = false;
    }
  }, [enabled]);

  // Hold a stable ref to the abort helper so the enabled effect can call it
  const stopRecognizerRef = useRef(null);
  const stopRecognizer = () => {
    if (stopRecognizerRef.current) stopRecognizerRef.current();
  };

  useEffect(() => {
    let rec              = null;
    let cancelled        = false;
    let restartTimer     = null;
    let keepAlive        = null;
    let noSpeechStreak   = 0;
    let networkErrors    = 0;

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

    // ── Browser recognizer teardown ─────────────────────────────────────
    const teardownBrowserRec = () => {
      if (rec) {
        rec.onend    = null;
        rec.onerror  = null;
        rec.onresult = null;
        try { rec.abort(); } catch (_) {}
        rec = null;
      }
    };

    // ── Whisper-mode teardown (stream / VAD / recorder) ──────────────────
    const teardownWhisper = () => {
      if (vadFrameRef.current) {
        cancelAnimationFrame(vadFrameRef.current);
        vadFrameRef.current = null;
      }
      if (recorderRef.current) {
        try { recorderRef.current.onstop = null; recorderRef.current.stop(); } catch (_) {}
        recorderRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => { try { t.stop(); } catch (_) {} });
        streamRef.current = null;
      }
      if (audioCtxRef.current) {
        try { audioCtxRef.current.close(); } catch (_) {}
        audioCtxRef.current = null;
        analyserRef.current = null;
      }
      activeRef.current = false;
    };

    stopRecognizerRef.current = () => {
      if (restartTimer) { clearTimeout(restartTimer); restartTimer = null; }
      teardownBrowserRec();
      teardownWhisper();
    };

    const scheduleRestart = (ms) => {
      if (cancelled || restartTimer || !enabledRef.current) return;
      if (listeningModeRef.current === 'ptt') return; // PTT never auto-restarts
      restartTimer = setTimeout(() => {
        restartTimer = null;
        if (!cancelled && enabledRef.current) startAfterIdle();
      }, ms);
    };

    // ── Shared transcript pipeline (both engines feed this) ─────────────
    const processTranscript = async (rawTranscript) => {
      if (!enabledRef.current || !rawTranscript) return;
      const normRaw = rawTranscript.toLowerCase().trim();
      if (!normRaw) return;

      console.log('[Voice] Raw speech recognized:', rawTranscript);

      // 🛡️ SELF-ECHO REJECTION GUARD:
      // Ignore audio if it's FRIDAY's own spoken TTS output or matches recent response
      const now = Date.now();
      const spokenInfo = lastSpokenTtsRef.current;
      const isRecentTts = spokenInfo.text && (now - spokenInfo.ts < 5000);
      const containsTtsSnippet = isRecentTts && (
        normRaw.includes(spokenInfo.text) ||
        spokenInfo.text.includes(normRaw) ||
        /\b(?:brightness|set to|percent|standing by|prem|at your service|opening|closing|system is locked|enabled|disabled|locking display)\b/.test(normRaw)
      );

      // 🛡️ SELF-ECHO REJECTION + TRUE BARGE-IN:
      // Audio matching FRIDAY's own recent TTS output is always her echo — block it.
      if (containsTtsSnippet) {
        console.log('[Voice Self-Echo Blocked] Suppressing speaker audio capture:', rawTranscript);
        return;
      }

      if (speakingRef.current) {
        // Explicit user stop command ("stop", "shut up"…) — always honored.
        const isExplicitStop = /\b(?:stop|shut up|quiet|pause|hush|wait|baat band)\b/.test(normRaw);
        if (isExplicitStop) {
          console.log('[Voice Interrupt] 🛑 User explicit stop command — aborting TTS.');
          stopSpeaking();
          speakingRef.current = false;
          lastSpokenTtsRef.current = { text: '', ts: 0 };
          setTtsDucking(false);
          return;
        }

        // TRUE BARGE-IN: FRIDAY is speaking but this is the USER's voice
        // (doesn't match her speech and looks like a command) → stop her
        // instantly and listen. Wake word / commands only — never noise.
        if (!COMMAND_LIKE.test(normRaw)) {
          console.log('[Voice Self-Echo Blocked] Suppressing speaker audio capture:', rawTranscript);
          return;
        }

        console.log('[Voice Barge-In] 🎙 User speech during TTS — stopping FRIDAY and listening:', rawTranscript);
        stopSpeaking();
        speakingRef.current = false;
        lastSpokenTtsRef.current = { text: '', ts: 0 };
        setTtsDucking(false);
        // fall through → the user's command is processed below
      }

      // ── Wake-word stripping ─────────────────────────────────────────────
      let query = rawTranscript.trim()
        .replace(/^ready\s*(?:film|feel|fill)/i, 'play')
        .replace(/^if\s+friday\s+please/i, 'play')
        .replace(/^suno\s+friday/i, '')
        .replace(/^(?:if|he|hey|hi|hello|ok|okay|sun|suno|aye)?\s*(?:friday|fraide|frida|freddy|frieda|freddie|freya|phiday|fri\s*day)\b\s*/gi, '')
        .trim();

      if (!query) {
        console.log('[Voice Interrupt] Wake-word only — listening for command...');
        noSpeechStreak = 0;
        return;
      }

      // ── Minimal Noise Filter (grunts only) ──────────────────────────────
      const NOISE_ONLY = new Set(['uh', 'um', 'hmm', 'hm', 'ah', 'oh']);
      if (NOISE_ONLY.has(query.toLowerCase().trim())) {
        console.log('[Voice] Ignored grunt noise:', query);
        return;
      }

      // ── Dedup guard ─────────────────────────────────────────────────────
      const lastRaw = lastTranscriptRef.current;
      if (lastRaw && lastRaw.text === rawTranscript.trim() && now - lastRaw.ts < 3000) {
        console.log('[Voice] Suppressing duplicate transcript within 3s:', rawTranscript);
        return;
      }
      lastTranscriptRef.current = { text: rawTranscript.trim(), ts: now };

      if (/^at\s+this\s+song/i.test(query)) {
        query = query.replace(/^at\s+this\s+song/i, 'add this song');
      }

      console.log('[Voice] Valid command recognized:', rawTranscript.trim(), '-> query:', query);

      if (query.length > 0) {
        if (window.fridayCheckPendingConfirmation) {
          const handled = await window.fridayCheckPendingConfirmation(query);
          if (handled) {
            console.log('[Voice] Pending proactive action confirmed.');
            return;
          }
        }

        // Stop listening while the command is handled (mic comes back in
        // handleCmd's finally — during TTS — so the user can barge in).
        teardownBrowserRec();

        await handleCmd(query);
      }
    };

    // ── Speak a reply WITHOUT blocking the mic ───────────────────────────
    // Fire-and-forget: arms the self-echo guard, ducks TTS volume in Whisper
    // mode (so her own voice can't trigger barge-in), and lets the recognizer
    // keep listening — the user can interrupt her mid-sentence.
    const speakWithGuard = (text, timeoutMs) => {
      if (!text) return;
      lastSpokenTtsRef.current = { text: text.toLowerCase().trim(), ts: Date.now() };
      const gen = ++speechGenRef.current;
      speakingRef.current = true;
      setTtsDucking(modeRef.current === 'whisper');
      withTimeout(speak(text), timeoutMs)
        .catch(() => {})
        .finally(() => {
          // Only the latest reply may clear the speaking state (a stale
          // interrupted reply must not wipe a newer one's guard).
          if (gen === speechGenRef.current) {
            speakingRef.current = false;
            setTtsDucking(false);
          }
        });
    };

    // ── Command handler ───────────────────────────────────────────────────
    const handleCmd = async (cmd) => {
      const now = Date.now();
      if (processingRef.current || (cmd === lastProcessedCmd && now - lastProcessedTime < 3000)) {
        console.log('[Voice] Suppressing duplicate rapid command:', cmd);
        if (!activeRef.current) startAfterIdle();
        return;
      }
      processingRef.current = true;
      lastProcessedCmd = cmd;
      lastProcessedTime = now;

      try {
        const localCommand = matchVoiceCommand(cmd);
        if (localCommand) {
          // Handle object commands (open_app, close_app)
          if (typeof localCommand === 'object') {
            onCommandRef.current?.(localCommand);
            return;
          }

          const workspaceCommands = ['trading', 'dashboard', 'engineering', 'vscode', 'browser'];
          if (lockedRef.current && workspaceCommands.includes(localCommand)) {
            const lockedReply = 'System is locked, Boss. Please unlock first.';
            onConvRef.current?.({ transcript: cmd, reply: lockedReply, action: 'none' });
            
            // Register TTS self-echo guard (non-blocking → barge-in possible)
            speakWithGuard(lockedReply, 8000);
            return;
          }

          onCommandRef.current?.(localCommand);
          const reply = localCommand === 'trading'
            ? 'Opening Personal Trading Station, Prem.'
            : localCommand === 'dashboard'
            ? 'Opening Dashboard, Prem.'
            : localCommand === 'engineering'
            ? 'Opening Engineering Console, Prem.'
            : 'Executing command, Prem.';
          onConvRef.current?.({ transcript: cmd, reply, action: localCommand });

          speakWithGuard(reply, 10000);
          return;
        }

        const data   = await withTimeout(fetchChatText(cmd), 12000);
        const reply  = data.reply?.trim()  || 'At your service, Boss.';
        const action = data.action?.trim() || 'none';

        if (action && action !== 'none') onCommandRef.current?.(action);
        onConvRef.current?.({ transcript: cmd, reply, action });

        // ── Speak response (non-blocking → mic restarts while she talks,
        //    so the user can barge in) ─────────────────────────────────────
        if (!data.silence_tts) speakWithGuard(reply, 15000);
        noSpeechStreak = 0;

      } catch (err) {
        console.warn('[Voice] Command error:', err);
        speakingRef.current = false;
      } finally {
        processingRef.current = false;
        if (!cancelled && enabledRef.current && !activeRef.current) {
          startAfterIdle();
        }
      }
    };

    let lastProcessedCmd = '';
    let lastProcessedTime = 0;

    // ── Restart whatever engine is currently active ───────────────────────
    const startAfterIdle = () => {
      if (cancelled || !enabledRef.current || micBlockedRef.current) return;
      if (listeningModeRef.current === 'ptt') return; // PTT: mic opens only while held
      if (modeRef.current === 'whisper') startWhisper();
      else start();
    };

    // ══════════════════ ENGINE 1: BROWSER WEB SPEECH API ══════════════════
    const start = () => {
      if (cancelled || !enabledRef.current || micBlockedRef.current) return;

      if (!SpeechRec) {
        // Browser engine unavailable (Firefox, old webviews…) — use the
        // backend Whisper engine instead.
        console.warn('[Voice] SpeechRecognition not supported — switching to Whisper backend STT (Groq free tier).');
        modeRef.current = 'whisper';
        startWhisper();
        return;
      }

      teardownBrowserRec();

      rec = new SpeechRec();
      rec.continuous     = true;
      rec.interimResults = true; // interim for responsiveness; finals drive commands
      rec.lang           = 'en-US';

      rec.onstart = () => {
        console.log('[Voice] Microphone actively Listening...');
        activeRef.current = true;
        noSpeechStreak = 0;
      };

      rec.onerror = (e) => {
        activeRef.current = false;
        if (cancelled || !enabledRef.current || micBlockedRef.current) return;
        console.warn('[Voice] Recognition error:', e.error);

        if (e.error === 'no-speech') {
          noSpeechStreak += 1;
          if (noSpeechStreak >= 6) {
            console.log('[Voice] Browser STT repeatedly silent — switching to Whisper backend STT.');
            switchToWhisper('no-speech');
            return;
          }
          const delay = Math.min(500 * Math.pow(2, noSpeechStreak - 1), 5000);
          scheduleRestart(delay);
        } else if (e.error === 'network') {
          networkErrors += 1;
          if (networkErrors >= 2) {
            console.log('[Voice] Browser STT network failures — switching to Whisper backend STT.');
            switchToWhisper('network');
            return;
          }
          scheduleRestart(1000);
        } else if (e.error === 'not-allowed' || e.error === 'service-not-allowed' || e.error === 'audio-capture') {
          console.warn('[Voice] Microphone permission denied — voice disabled. Allow mic access to use voice.');
          micBlockedRef.current = true;
        } else {
          scheduleRestart(1200);
        }
      };

      rec.onend = () => {
        activeRef.current = false;
        if (cancelled || !enabledRef.current || micBlockedRef.current) return;
        if (modeRef.current !== 'browser') return; // engine switched underneath us
        const delay = noSpeechStreak > 0 ? Math.min(500 * noSpeechStreak, 3000) : 300;
        scheduleRestart(delay);
      };

      rec.onresult = (e) => {
        if (!enabledRef.current) return;

        // Collect final results only (interim transcripts are just logging).
        let finalText = '';
        let bestConfidence = 1;
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const res = e.results[i];
          if (!res.isFinal) {
            if (res[0]?.transcript) console.log('[Voice] Interim:', res[0].transcript);
            continue;
          }
          const t = res[0]?.transcript ?? '';
          if (t) {
            finalText += ' ' + t;
            bestConfidence = Math.min(bestConfidence, Number(res[0].confidence) || 1);
          }
        }
        finalText = finalText.trim();
        if (!finalText) return;

        console.log(`[Voice] Final transcript (confidence ${bestConfidence.toFixed(2)}):`, finalText);

        // Low-confidence short utterances are usually room noise / false wake.
        if (bestConfidence < 0.4 && finalText.split(/\s+/).length <= 2) {
          console.log('[Voice] Low-confidence short utterance ignored as noise.');
          return;
        }

        // NOTE: recognizer is intentionally NOT torn down here — it stays
        // live so the user can barge in while FRIDAY is speaking. It's torn
        // down in processTranscript only when a command is actually handled.
        noSpeechStreak = 0;
        processTranscript(finalText);
      };

      try {
        rec.start();
      } catch (err) {
        console.warn('[Voice] start() threw:', err.message || err);
        scheduleRestart(800);
      }
    };

    // ══════════════════ PUSH-TO-TALK (HOLD SPACE) ═════════════════════════
    const notifyPtt = (held) => {
      try { window.dispatchEvent(new CustomEvent('friday-ptt', { detail: { held } })); } catch (_) {}
    };

    // PTT session — browser engine: single-utterance recognizer, finalized on release.
    const startPttBrowser = () => {
      if (cancelled || !enabledRef.current) return;
      if (!SpeechRec) {
        // Browser engine unavailable — record the clip with the Whisper engine instead.
        modeRef.current = 'whisper';
        startWhisper();
        return;
      }

      teardownBrowserRec();

      let finals = '';
      let interim = '';
      const sessionRec = new SpeechRec();
      sessionRec.continuous     = false; // one utterance per hold
      sessionRec.interimResults = true;
      sessionRec.lang           = 'en-US';

      sessionRec.onstart = () => { activeRef.current = true; };

      sessionRec.onerror = (e) => {
        activeRef.current = false;
        if (cancelled) return;
        console.warn('[Voice][PTT] Recognition error:', e.error);
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed' || e.error === 'audio-capture') {
          micBlockedRef.current = true;
        }
        // 'no-speech' / 'network' — the PTT session just ends without a transcript.
      };

      sessionRec.onresult = (e) => {
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const res = e.results[i];
          const t = res[0]?.transcript ?? '';
          if (res.isFinal) finals += ' ' + t;
          else if (t) interim = t;
        }
      };

      sessionRec.onend = () => {
        activeRef.current = false;
        if (cancelled) return;
        const text = (finals.trim() || interim.trim());
        if (text) processTranscript(text);
        // No auto-restart — PTT is strictly hold-to-talk.
      };

      rec = sessionRec;
      try {
        sessionRec.start();
      } catch (err) {
        console.warn('[Voice][PTT] start() threw:', err?.message || err);
        rec = null;
      }
    };

    const pttStart = () => {
      if (cancelled || !enabledRef.current || micBlockedRef.current) return;
      if (pttSessionRef.current.active) return;

      // Barge-in: holding the key while FRIDAY is speaking stops her instantly.
      stopSpeaking();
      speakingRef.current = false;
      lastSpokenTtsRef.current = { text: '', ts: 0 }; // her words must not block the held utterance
      setTtsDucking(false);

      pttSessionRef.current.active = true;
      notifyPtt(true);
      console.log('[Voice][PTT] 🎙 Held — listening...');

      if (modeRef.current === 'whisper') {
        startWhisper();
      } else {
        startPttBrowser();
      }
    };

    const pttEnd = () => {
      if (!pttSessionRef.current.active) return;
      pttSessionRef.current.active = false;
      notifyPtt(false);
      console.log('[Voice][PTT] Released — finalizing...');

      if (modeRef.current === 'whisper') {
        if (recorderRef.current) {
          stopRecorder();
        } else {
          // Mic was still starting up — close it right away.
          teardownWhisper();
        }
      } else if (rec) {
        try { rec.stop(); } catch (_) {} // finalize the utterance
      }
    };

    // ── Global hold-to-talk key handling ──────────────────────────────────
    const isInteractiveTarget = () => {
      const el = document.activeElement;
      if (!el || el === document.body) return false;
      const tag = el.tagName;
      return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
        || tag === 'BUTTON' || tag === 'A' || el.isContentEditable;
    };

    const onKeyDown = (e) => {
      if (e.code !== 'Space' || e.repeat) return;
      if (listeningModeRef.current !== 'ptt' || !enabledRef.current) return;
      if (isInteractiveTarget()) return; // don't hijack Space in inputs/buttons
      e.preventDefault(); // stop page scroll while holding
      pttStart();
    };

    const onKeyUp = (e) => {
      if (e.code !== 'Space') return;
      pttEnd();
    };

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);

    // ══════════════════ ENGINE 2: WHISPER BACKEND (GROQ FREE TIER) ══════════════════
    const switchToWhisper = (reason) => {
      if (cancelled || !enabledRef.current || micBlockedRef.current) return;
      if (modeRef.current === 'whisper') return;
      console.log(`[Voice] Switching to Whisper backend STT (reason: ${reason}) — Groq free tier / Gemini fallback.`);
      modeRef.current = 'whisper';
      teardownBrowserRec();
      startWhisper();
    };

    const VAD_RMS_THRESHOLD = 0.025;  // voice activity threshold (RMS)
    const VAD_RMS_BARGE_IN  = 0.05;   // louder threshold while FRIDAY is talking (barge-in)
    const VAD_SILENCE_MS    = 900;    // silence that ends a clip
    const VAD_MIN_SPEECH_MS = 300;    // ignore sub-300ms blips
    const VAD_MAX_CLIP_MS   = 15000;  // safety cap per clip

    const pickRecorderMime = () => {
      const candidates = ['audio/ogg;codecs=opus', 'audio/webm;codecs=opus', 'audio/mp4'];
      if (typeof MediaRecorder === 'undefined') return '';
      for (const m of candidates) {
        try { if (MediaRecorder.isTypeSupported(m)) return m; } catch (_) {}
      }
      return '';
    };

    const startWhisper = async () => {
      if (cancelled || !enabledRef.current || micBlockedRef.current) return;
      if (streamRef.current && activeRef.current) return; // already live

      teardownWhisper();

      if (!navigator.mediaDevices?.getUserMedia) {
        console.warn('[Voice] mediaDevices unavailable (insecure context?) — Whisper STT unavailable.');
        micBlockedRef.current = true;
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        });
        if (cancelled || !enabledRef.current) { stream.getTracks().forEach(t => t.stop()); return; }
        // PTT: user released the key while the mic was still starting — close it.
        if (listeningModeRef.current === 'ptt' && !pttSessionRef.current.active) {
          stream.getTracks().forEach(t => t.stop());
          return;
        }
        streamRef.current = stream;

        const Ctx = window.AudioContext || window.webkitAudioContext;
        const ctx = new Ctx();
        audioCtxRef.current = ctx;
        const source = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 2048;
        source.connect(analyser);
        analyserRef.current = analyser;

        activeRef.current = true;
        noSpeechStreak = 0;
        console.log('[Voice] Whisper mic active — listening for speech segments (Groq Whisper free tier).');
        vadLoop();
      } catch (err) {
        console.warn('[Voice] Mic unavailable for Whisper mode:', err?.message || err);
        activeRef.current = false;
        teardownWhisper();
        if (err?.name === 'NotAllowedError' || err?.name === 'SecurityError') {
          micBlockedRef.current = true;
          console.warn('[Voice] Microphone permission denied — voice disabled.');
        }
      }
    };

    // ── Voice activity detection loop (AnalyserNode RMS) ─────────────────
    const vadLoop = () => {
      if (cancelled || !enabledRef.current || modeRef.current !== 'whisper') {
        vadFrameRef.current = null;
        return;
      }
      const analyser = analyserRef.current;
      const ctx = audioCtxRef.current;
      if (!analyser || !ctx || !streamRef.current) { vadFrameRef.current = null; return; }

      const buf = new Uint8Array(analyser.fftSize);
      analyser.getByteTimeDomainData(buf);
      let sum = 0;
      for (let i = 0; i < buf.length; i++) {
        const v = (buf[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / buf.length);
      const now = Date.now();
      const vad = vadRef.current;
      const isSpeaking = speakingRef.current;

      // Track recent quiet frames so barge-in only fires on a FRESH voice
      // onset (FRIDAY's own ducked TTS won't trip it mid-sentence).
      if (rms < VAD_RMS_THRESHOLD) vad.quietFrames = Math.min(vad.quietFrames + 1, 8);
      else vad.quietFrames = 0;

      // Don't start clips while a command is being processed
      const blocked = processingRef.current;

      // ── PTT mode: record ONLY while Space is held (no VAD triggering) ───
      if (listeningModeRef.current === 'ptt') {
        if (pttSessionRef.current.active && !blocked) {
          if (vad.state !== 'speech') {
            vad.state = 'speech';
            vad.speechStart = now;
            vad.lastVoice = now;
            startRecorder();
          }
        }
        vadFrameRef.current = requestAnimationFrame(vadLoop);
        return;
      }

      // ── TRUE BARGE-IN: fresh, loud voice onset while FRIDAY is talking
      //    → stop her instantly and record the user's words ──────────────
      if (!blocked && isSpeaking && rms > VAD_RMS_BARGE_IN && vad.quietFrames >= 3) {
        console.log('[Voice Barge-In] 🎙 Voice onset during TTS — interrupting FRIDAY.');
        stopSpeaking();
        speakingRef.current = false;
        lastSpokenTtsRef.current = { text: '', ts: 0 };
        setTtsDucking(false);
        vad.state = 'speech';
        vad.speechStart = now;
        vad.lastVoice = now;
        startRecorder();
      } else if (!blocked && !isSpeaking && rms > VAD_RMS_THRESHOLD) {
        if (vad.state === 'idle') {
          vad.state = 'speech';
          vad.speechStart = now;
          vad.lastVoice = now;
          startRecorder();
        } else {
          vad.lastVoice = now;
        }
      } else if (vad.state === 'speech') {
        const dur = now - vad.speechStart;
        const silentFor = now - vad.lastVoice;
        if (dur > VAD_MIN_SPEECH_MS && (silentFor > VAD_SILENCE_MS || dur > VAD_MAX_CLIP_MS)) {
          vad.state = 'idle';
          stopRecorder();
        }
      }

      vadFrameRef.current = requestAnimationFrame(vadLoop);
    };

    const startRecorder = () => {
      if (recorderRef.current || !streamRef.current) return;
      try {
        const mime = pickRecorderMime();
        const rec = mime
          ? new MediaRecorder(streamRef.current, { mimeType: mime })
          : new MediaRecorder(streamRef.current);
        chunksRef.current = [];

        rec.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
        };

        rec.onstop = async () => {
          recorderRef.current = null;
          const blob = new Blob(chunksRef.current, { type: rec.mimeType || 'audio/ogg' });
          chunksRef.current = [];
          if (blob.size === 0) return;

          const mimeType = rec.mimeType || '';
          const ext = mimeType.includes('mp4') ? 'clip.m4a'
            : mimeType.includes('webm') ? 'clip.webm'
            : 'clip.ogg';
          console.log('[Voice] Whisper clip captured:', (blob.size / 1024).toFixed(0) + ' KB');

          try {
            const transcript = await withTimeout(transcribeAudioBlob(blob, ext), 20000);
            if (transcript) {
              await processTranscript(transcript);
            } else {
              console.log('[Voice] Whisper returned empty transcript — ignoring.');
            }
          } catch (err) {
            console.warn('[Voice] Whisper transcription failed:', err?.message || err);
            // Free-tier rate limit (429) — back off briefly before next clip.
            if (/429|Too many|rate.?limit/i.test(err?.message || '')) {
              await new Promise(r => setTimeout(r, 3000));
            }
          } finally {
            // PTT: close the mic after each clip — it only lives while held.
            // (Unless a new hold already started; then keep the stream.)
            if (listeningModeRef.current === 'ptt' && !pttSessionRef.current.active) {
              teardownWhisper();
            }
          }
        };

        rec.start(200); // timeslice → periodic dataavailable chunks
        recorderRef.current = rec;
      } catch (err) {
        console.warn('[Voice] Recorder start failed:', err?.message || err);
      }
    };

    const stopRecorder = () => {
      const rec = recorderRef.current;
      if (!rec) return;
      try { rec.stop(); } catch (_) { recorderRef.current = null; }
    };

    // ── Watchdog: revive if mic silently died (never in PTT mode) ─────────
    keepAlive = setInterval(() => {
      if (!enabledRef.current || micBlockedRef.current) return;
      if (listeningModeRef.current === 'ptt') return;
      if (activeRef.current || processingRef.current || speakingRef.current) return;
      if (modeRef.current === 'whisper') {
        console.log('[Voice Watchdog] Whisper mic inactive, reviving...');
        startWhisper();
      } else {
        console.log('[Voice Watchdog] Mic inactive, reviving...');
        start();
      }
    }, 5000);

    const bootTimer = setTimeout(() => {
      // PTT mode never auto-opens the mic — it waits for the Space hold.
      if (enabledRef.current && listeningModeRef.current !== 'ptt') startAfterIdle();
    }, 0);

    return () => {
      cancelled = true;
      activeRef.current    = false;
      speakingRef.current  = false;
      pttSessionRef.current.active = false;
      stopRecognizerRef.current = null;
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
      if (keepAlive)    clearInterval(keepAlive);
      if (restartTimer) clearTimeout(restartTimer);
      if (bootTimer)    clearTimeout(bootTimer);
      teardownBrowserRec();
      teardownWhisper();
    };
  }, []);
}
