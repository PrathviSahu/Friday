import { useEffect, useRef } from 'react';
import { matchVoiceCommand } from './voiceCommands';
import { fetchChatText } from '../api/chatText';
import { speak } from '../services/ttsService';

const withTimeout = (promise, ms) =>
  Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`Operation timed out after ${ms}ms`)), ms)
    ),
  ]);

export function useSpeech({ isLocked, onCommand, onConversation }) {
  const activeRef     = useRef(false);   // true while SpeechRecognition is running
  const processingRef = useRef(false);   // true while a command is being handled
  const speakingRef   = useRef(false);   // true while FRIDAY's TTS is playing
  const lockedRef     = useRef(isLocked);
  const onCommandRef  = useRef(onCommand);
  const onConvRef     = useRef(onConversation);

  useEffect(() => { lockedRef.current = isLocked; }, [isLocked]);
  useEffect(() => { onCommandRef.current = onCommand; }, [onCommand]);
  useEffect(() => { onConvRef.current = onConversation; }, [onConversation]);

  useEffect(() => {
    let rec           = null;
    let cancelled     = false;
    let restartTimer  = null;   // only ONE restart ever pending at a time
    let keepAlive     = null;

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.warn('[Voice] SpeechRecognition not supported in this browser.');
      return;
    }

    // ── Schedule exactly one restart ──────────────────────────────────────────
    const scheduleRestart = (ms) => {
      if (cancelled || restartTimer) return;          // one pending max
      restartTimer = setTimeout(() => {
        restartTimer = null;
        if (!speakingRef.current) start();            // don't restart while TTS plays
      }, ms);
    };

    // ── Create and boot a fresh SpeechRecognition instance ───────────────────
    const start = () => {
      if (cancelled || speakingRef.current) return;  // never start while FRIDAY speaks

      // Silence old instance BEFORE abort so its onend/onerror don't trigger more restarts
      if (rec) {
        rec.onend   = null;
        rec.onerror = null;
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
      };

      rec.onerror = (e) => {
        activeRef.current = false;
        if (cancelled) return;
        console.warn('[Voice] Recognition error:', e.error);
        // aborted = we triggered it ourselves — ignore.  network/no-speech = retry.
        if (e.error === 'no-speech' || e.error === 'network') {
          scheduleRestart(300);
        }
        // 'aborted' is swallowed — onend will fire and handle it
      };

      rec.onend = () => {
        activeRef.current = false;
        if (cancelled) return;
        console.log('[Voice] Recognition ended, scheduling restart...');
        scheduleRestart(250);
      };

      rec.onresult = (e) => {
        // Suppress any result while FRIDAY is speaking (self-echo guard)
        if (speakingRef.current) {
          console.log('[Voice] Suppressing echo — FRIDAY is speaking.');
          return;
        }

        const idx = e.resultIndex ?? 0;
        const rawTranscript = e.results[idx]?.[0]?.transcript ?? '';
        if (!rawTranscript.trim()) return;

        console.log('[Voice] Raw speech recognized:', rawTranscript);

        // Strip wake-words: "if friday", "hey friday", "friday", etc.
        let query = rawTranscript.trim()
          .replace(/^(?:if|he|hey|hi|hello|ok|okay)\s+friday\b\s*/i, '')
          .replace(/^friday\b\s*/i, '')
          .trim();

        // Normalise transcript for logging
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
        console.warn('[Voice] start() threw:', err);
        scheduleRestart(500);
      }
    };

    // ── Watchdog: restart if mic silently died ────────────────────────────────
    keepAlive = setInterval(() => {
      if (!cancelled && !activeRef.current && !processingRef.current && !speakingRef.current) {
        console.log('[Voice Watchdog] Mic inactive — restarting...');
        start();
      }
    }, 3000);

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

        const data = await withTimeout(fetchChatText(cmd), 12000);
        const reply  = data.reply?.trim()  || 'At your service, Boss.';
        const action = data.action?.trim() || 'none';

        if (action && action !== 'none') {
          onCommandRef.current?.(action);
        }

        onConvRef.current?.({ transcript: cmd, reply, action });

        // ── PAUSE mic while speaking, resume cleanly after ──────────────────
        speakingRef.current = true;
        // Stop the running recognizer so it doesn't pick up FRIDAY's voice
        if (rec) {
          rec.onend   = null;   // silence the handler temporarily
          rec.onerror = null;
          rec.onresult = null;
          try { rec.stop(); } catch (_) {}
          activeRef.current = false;
        }

        try { await withTimeout(speak(reply), 15000); } catch (_) {}

        speakingRef.current = false;

        // Short silence buffer after TTS ends before we start listening again
        await new Promise(r => setTimeout(r, 400));
        if (!cancelled) start();

      } catch (err) {
        console.warn('[Voice] Command error:', err);
        speakingRef.current = false;
      } finally {
        processingRef.current = false;
      }
    };

    // Boot immediately
    const bootTimer = setTimeout(start, 0);

    return () => {
      cancelled = true;
      activeRef.current = false;
      speakingRef.current = false;
      if (keepAlive)    clearInterval(keepAlive);
      if (restartTimer) clearTimeout(restartTimer);
      clearTimeout(bootTimer);
      if (rec) {
        rec.onend = null; rec.onerror = null; rec.onresult = null;
        try { rec.abort(); } catch (_) {}
      }
    };
  }, []);
}