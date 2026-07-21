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

export function useSpeech({ isLocked, onCommand, onConversation }) {
  const activeRef     = useRef(false);  // true while SpeechRecognition is running
  const processingRef = useRef(false);  // true while a command is being handled
  const speakingRef   = useRef(false);  // true while FRIDAY's TTS is playing
  const lockedRef     = useRef(isLocked);
  const onCommandRef  = useRef(onCommand);
  const onConvRef     = useRef(onConversation);

  useEffect(() => { lockedRef.current = isLocked; }, [isLocked]);
  useEffect(() => { onCommandRef.current = onCommand; }, [onCommand]);
  useEffect(() => { onConvRef.current = onConversation; }, [onConversation]);

  useEffect(() => {
    let rec              = null;
    let cancelled        = false;
    let restartTimer     = null;    // only ONE pending restart at a time
    let keepAlive        = null;
    let noSpeechStreak   = 0;       // consecutive no-speech errors → exponential back-off

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.warn('[Voice] SpeechRecognition not supported in this browser.');
      return;
    }

    // ── Schedule at most one pending restart ─────────────────────────────────
    const scheduleRestart = (ms) => {
      if (cancelled || restartTimer) return;   // already one pending — skip
      restartTimer = setTimeout(() => {
        restartTimer = null;
        if (!cancelled && !speakingRef.current) start();
      }, ms);
    };

    // ── Create and boot a fresh SpeechRecognition instance ───────────────────
    const start = () => {
      if (cancelled || speakingRef.current) return;

      // Silence old instance BEFORE abort so its onend/onerror don't fire
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
        noSpeechStreak = 0;   // reset back-off on successful start
      };

      rec.onerror = (e) => {
        activeRef.current = false;
        if (cancelled) return;
        console.warn('[Voice] Recognition error:', e.error);

        if (e.error === 'no-speech') {
          // Exponential back-off: 500ms → 1s → 2s → 4s, max 5s
          noSpeechStreak += 1;
          const delay = Math.min(500 * Math.pow(2, noSpeechStreak - 1), 5000);
          console.log(`[Voice] no-speech streak=${noSpeechStreak}, retrying in ${delay}ms`);
          scheduleRestart(delay);
        } else if (e.error === 'network') {
          scheduleRestart(1000);
        }
        // 'aborted' is intentional (we caused it) — let onend handle the restart
      };

      rec.onend = () => {
        activeRef.current = false;
        if (cancelled) return;
        console.log('[Voice] Recognition ended, scheduling restart...');
        // Use longer delay if we're in a no-speech streak so Chrome doesn't throttle
        const delay = noSpeechStreak > 0 ? Math.min(500 * noSpeechStreak, 3000) : 300;
        scheduleRestart(delay);
      };

      rec.onresult = (e) => {
        // Self-echo guard: drop anything while FRIDAY is speaking
        if (speakingRef.current) {
          console.log('[Voice] Suppressing echo — FRIDAY is speaking.');
          return;
        }

        noSpeechStreak = 0;   // real speech received — reset back-off

        const idx = e.resultIndex ?? 0;
        const rawTranscript = e.results[idx]?.[0]?.transcript ?? '';
        if (!rawTranscript.trim()) return;

        console.log('[Voice] Raw speech recognized:', rawTranscript);

        // Strip wake-words: "if friday", "hey friday", "friday", etc.
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
      if (!cancelled && !activeRef.current && !processingRef.current && !speakingRef.current && !restartTimer) {
        console.log('[Voice Watchdog] Mic inactive — restarting...');
        noSpeechStreak = 0;
        start();
      }
    }, 5000);   // 5s — generous so we don't fight the back-off

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

        const data  = await withTimeout(fetchChatText(cmd), 12000);
        const reply  = data.reply?.trim()  || 'At your service, Boss.';
        const action = data.action?.trim() || 'none';

        if (action && action !== 'none') onCommandRef.current?.(action);
        onConvRef.current?.({ transcript: cmd, reply, action });

        // ── Pause mic during TTS so we don't hear FRIDAY's own voice ─────────
        speakingRef.current = true;
        if (rec) {
          rec.onend    = null;   // silence handlers while we deliberately stop
          rec.onerror  = null;
          rec.onresult = null;
          try { rec.stop(); } catch (_) {}
          activeRef.current = false;
        }

        try { await withTimeout(speak(reply), 15000); } catch (_) {}

        speakingRef.current = false;
        noSpeechStreak = 0;   // fresh start after TTS

        // Brief buffer so FRIDAY's voice echo fades before mic opens
        await new Promise(r => setTimeout(r, 600));
        if (!cancelled) start();

      } catch (err) {
        console.warn('[Voice] Command error:', err);
        speakingRef.current = false;
        if (!cancelled) scheduleRestart(500);
      } finally {
        processingRef.current = false;
      }
    };

    const bootTimer = setTimeout(start, 0);

    return () => {
      cancelled = true;
      activeRef.current    = false;
      speakingRef.current  = false;
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