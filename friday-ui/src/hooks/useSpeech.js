import { useEffect, useRef } from 'react';
import { matchVoiceCommand } from './voiceCommands';
import { fetchChatText } from '../api/chatText';
import { speak } from '../services/ttsService';

const withTimeout = (promise, ms) =>
  Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`Timeout after ${ms}ms`)), ms)
    ),
  ]);

export function useSpeech({ locked, isLocked, enabled = true, onCommand, onConversation }) {
  // Support both prop name variants: locked (LockScreen) and isLocked (legacy)
  const _locked = locked ?? isLocked ?? false;
  const activeRef     = useRef(false);  // true while SpeechRecognition is running
  const processingRef = useRef(false);  // true while a command is being handled
  const speakingRef   = useRef(false);  // true while FRIDAY's TTS is playing
  const enabledRef    = useRef(enabled); // mirrors the enabled prop reactively
  const lockedRef     = useRef(_locked);
  const onCommandRef  = useRef(onCommand);
  const onConvRef     = useRef(onConversation);

  // Keep refs in sync with props every render — no re-mount needed
  useEffect(() => { lockedRef.current = _locked; }, [_locked]);
  useEffect(() => { onCommandRef.current = onCommand; }, [onCommand]);
  useEffect(() => { onConvRef.current = onConversation; }, [onConversation]);

  // When enabled flips OFF → abort recognizer immediately.
  // When it flips ON  → let the inner loop restart via scheduleRestart.
  useEffect(() => {
    enabledRef.current = enabled;
    if (!enabled) {
      // Hard-stop: abort is caught below by the silenced handlers, no restart scheduled
      stopRecognizer();
    }
  }, [enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  // Hold a stable ref to the abort helper so the enabled effect can call it
  const stopRecognizerRef = useRef(null);
  const stopRecognizer = () => {
    if (stopRecognizerRef.current) stopRecognizerRef.current();
  };

  useEffect(() => {
    let rec              = null;
    let cancelled        = false;
    let restartTimer     = null;    // only ONE pending restart at a time
    let keepAlive        = null;
    let noSpeechStreak   = 0;       // consecutive no-speech errors → exponential back-off

    // Register the abort helper so the enabled-toggle effect can reach it
    stopRecognizerRef.current = () => {
      if (restartTimer) { clearTimeout(restartTimer); restartTimer = null; }
      if (rec) {
        rec.onend    = null;
        rec.onerror  = null;
        rec.onresult = null;
        try { rec.abort(); } catch (_) {}
        activeRef.current = false;
      }
    };

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.warn('[Voice] SpeechRecognition not supported in this browser.');
      return;
    }

    // ── Schedule at most one pending restart ─────────────────────────────────
    const scheduleRestart = (ms) => {
      if (cancelled || restartTimer || !enabledRef.current) return;
      restartTimer = setTimeout(() => {
        restartTimer = null;
        if (!cancelled && !speakingRef.current && enabledRef.current) start();
      }, ms);
    };

    // ── Create and boot a fresh SpeechRecognition instance ───────────────────
    const start = () => {
      if (cancelled || speakingRef.current || !enabledRef.current) return;

      // Silence old instance BEFORE abort so its onend/onerror don't re-fire
      if (rec) {
        rec.onend    = null;
        rec.onerror  = null;
        rec.onresult = null;
        try { rec.abort(); } catch (_) {}
      }

      rec = new SpeechRec();
      rec.continuous     = true;
      rec.interimResults = false;
      rec.lang           = 'en-US';

      rec.onstart = () => {
        console.log('[Voice] Microphone actively Listening...');
        activeRef.current = true;
        noSpeechStreak = 0;
      };

      rec.onerror = (e) => {
        activeRef.current = false;
        if (cancelled || !enabledRef.current) return;
        console.warn('[Voice] Recognition error:', e.error);

        if (e.error === 'no-speech') {
          // Exponential back-off: 500 → 1000 → 2000 → 4000 → 5000ms cap
          noSpeechStreak += 1;
          const delay = Math.min(500 * Math.pow(2, noSpeechStreak - 1), 5000);
          console.log(`[Voice] no-speech streak=${noSpeechStreak}, retrying in ${delay}ms`);
          scheduleRestart(delay);
        } else if (e.error === 'network') {
          scheduleRestart(1000);
        }
        // 'aborted' is intentional — let onend handle cleanup
      };

      rec.onend = () => {
        activeRef.current = false;
        if (cancelled || !enabledRef.current) return;
        console.log('[Voice] Recognition ended, scheduling restart...');
        const delay = noSpeechStreak > 0 ? Math.min(500 * noSpeechStreak, 3000) : 300;
        scheduleRestart(delay);
      };

      rec.onresult = (e) => {
        // Mic is "off" or FRIDAY is speaking — drop the result
        if (!enabledRef.current || speakingRef.current) {
          console.log('[Voice] Suppressing result — mic disabled or FRIDAY speaking.');
          return;
        }

        noSpeechStreak = 0;

        const idx = e.resultIndex ?? 0;
        const rawTranscript = e.results[idx]?.[0]?.transcript ?? '';
        if (!rawTranscript.trim()) return;

        console.log('[Voice] Raw speech recognized:', rawTranscript);

        let query = rawTranscript.trim()
          .replace(/^(?:if|he|hey|hi|hello|ok|okay)\s+friday\b\s*/i, '')
          .replace(/^friday\b\s*/i, '')
          .trim();

        const normalized = query.toLowerCase();
        console.log('[Voice] Transcript:', rawTranscript.trim(), '-> normalized:', normalized);

        if (query.length > 0) {
          console.log('[Voice] Clean query sent to AI (wake-word removed):', query);
          handleCmd(query);
        }
      };

      try {
        rec.start();
      } catch (err) {
        console.warn('[Voice] start() threw:', err.message || err);
        scheduleRestart(800);
      }
    };

    // ── Watchdog: revive if mic silently died ─────────────────────────────────
    keepAlive = setInterval(() => {
      if (!cancelled && enabledRef.current && !activeRef.current && !processingRef.current && !speakingRef.current && !restartTimer) {
        console.log('[Voice Watchdog] Mic inactive — restarting...');
        noSpeechStreak = 0;
        start();
      }
    }, 5000);

    // ── Command handler ───────────────────────────────────────────────────────
    const handleCmd = async (cmd) => {
      if (processingRef.current) return;
      processingRef.current = true;

      try {
        if (lockedRef.current) {
          const lockedReply = 'Access denied, Boss. Please authenticate with your fingerprint key first.';
          onConvRef.current?.({ transcript: cmd, reply: lockedReply, action: 'none' });
          speakingRef.current = true;
          try { await withTimeout(speak(lockedReply), 10000); } catch (_) {}
          speakingRef.current = false;
          return;
        }

        const localCommand = matchVoiceCommand(cmd);
        if (localCommand) {
          onCommandRef.current?.(localCommand);
          return;
        }

        const data   = await withTimeout(fetchChatText(cmd), 12000);
        const reply  = data.reply?.trim()  || 'At your service, Boss.';
        const action = data.action?.trim() || 'none';

        if (action && action !== 'none') onCommandRef.current?.(action);
        onConvRef.current?.({ transcript: cmd, reply, action });

        // ── Pause mic during TTS so FRIDAY's voice isn't re-captured ─────────
        speakingRef.current = true;
        if (rec) {
          rec.onend    = null;
          rec.onerror  = null;
          rec.onresult = null;
          try { rec.stop(); } catch (_) {}
          activeRef.current = false;
        }

        try { await withTimeout(speak(reply), 15000); } catch (_) {}

        speakingRef.current = false;
        noSpeechStreak = 0;

        // Brief echo fade buffer, then restart — but only if mic is still enabled
        await new Promise(r => setTimeout(r, 600));
        if (!cancelled && enabledRef.current) start();

      } catch (err) {
        console.warn('[Voice] Command error:', err);
        speakingRef.current = false;
        if (!cancelled && enabledRef.current) scheduleRestart(500);
      } finally {
        processingRef.current = false;
      }
    };

    // Boot immediately if enabled
    const bootTimer = setTimeout(() => { if (enabledRef.current) start(); }, 0);

    return () => {
      cancelled = true;
      activeRef.current    = false;
      speakingRef.current  = false;
      stopRecognizerRef.current = null;
      if (keepAlive)    clearInterval(keepAlive);
      if (restartTimer) clearTimeout(restartTimer);
      clearTimeout(bootTimer);
      if (rec) {
        rec.onend = null; rec.onerror = null; rec.onresult = null;
        try { rec.abort(); } catch (_) {}
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}