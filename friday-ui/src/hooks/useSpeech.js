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
  const activeRef = useRef(false);
  const processingRef = useRef(false);
  const isSpeakingRef = useRef(false);
  const lockedRef = useRef(isLocked);
  const onCommandRef = useRef(onCommand);
  const onConversationRef = useRef(onConversation);

  useEffect(() => {
    lockedRef.current = isLocked;
  }, [isLocked]);

  useEffect(() => {
    onCommandRef.current = onCommand;
  }, [onCommand]);

  useEffect(() => {
    onConversationRef.current = onConversation;
  }, [onConversation]);

  useEffect(() => {
    let rec = null;
    let cancelled = false;
    let keepAliveTimer = null;
    let restartTimer = null;

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.warn('[Voice] SpeechRecognition not supported in this browser environment');
      return;
    }

    const scheduleRestart = (ms) => {
      if (cancelled || restartTimer) return;
      restartTimer = setTimeout(() => {
        restartTimer = null;
        start();
      }, ms);
    };

    const start = () => {
      if (cancelled) return;

      // FIX #1: Silence old instance handlers BEFORE aborting to eliminate restart storms!
      if (rec) {
        rec.onend = null;
        rec.onerror = null;
        rec.onresult = null;
        try { rec.abort(); } catch (_) {}
      }

      rec = new SpeechRec();
      rec.continuous = true;
      rec.interimResults = false;
      rec.lang = 'en-US';

      rec.onstart = () => {
        console.log('[Voice] Microphone actively listening...');
        activeRef.current = true;
      };

      rec.onerror = (e) => {
        console.warn('[Voice] Recognition error:', e.error);
        activeRef.current = false;
        // Schedule single restart
        if (!cancelled && (e.error === 'no-speech' || e.error === 'network' || e.error === 'aborted')) {
          scheduleRestart(300);
        }
      };

      rec.onend = () => {
        console.log('[Voice] Recognition ended, auto-restarting...');
        activeRef.current = false;
        scheduleRestart(250);
      };

      rec.onresult = (e) => {
        // FIX #4: Drop any speech transcript that arrives while FRIDAY herself is speaking!
        if (isSpeakingRef.current) {
          console.log('[Voice] Suppressing self-talk echo while FRIDAY is speaking...');
          return;
        }

        const resultIndex = e.resultIndex;
        if (resultIndex === undefined || resultIndex < 0) return;
        
        const rawTranscript = e.results[resultIndex][0].transcript;
        console.log('[Voice] Raw speech recognized:', rawTranscript);

        let query = rawTranscript.trim();
        query = query.replace(/^(?:he|hey|hi|hello|ok|okay)\s+friday\b\s*/i, '')
                     .replace(/^friday\b\s*/i, '')
                     .trim();

        if (query.length > 0) {
          console.log('[Voice] Clean query sent to AI (wake-word removed):', query);
          handleCmd(query);
        }
      };

      try {
        rec.start();
      } catch (e) {
        scheduleRestart(400);
      }
    };

    // Watchdog keep-alive loop (checks activeRef and forces restart if Chrome drops listener)
    keepAliveTimer = setInterval(() => {
      if (!cancelled && !activeRef.current && !processingRef.current) {
        console.log('[Voice Watchdog] Mic inactive, auto-restarting listener...');
        start();
      }
    }, 2500);

    const handleCmd = async (cmd) => {
      // FIX #3: Re-instated duplicate-command guard to prevent concurrent execution loops
      if (processingRef.current) return;

      processingRef.current = true;
      try {
        if (lockedRef.current) {
          const lockedReply = "Access denied, Boss. Please authenticate with your fingerprint key first.";
          onConversationRef.current?.({ transcript: cmd, reply: lockedReply, action: 'none' });
          
          isSpeakingRef.current = true;
          try {
            await withTimeout(speak(lockedReply), 8000);
          } finally {
            isSpeakingRef.current = false;
          }
          return;
        }

        const localCommand = matchVoiceCommand(cmd);
        if (localCommand) {
          onCommandRef.current?.(localCommand);
          return;
        }

        // FIX #2: Wrapped API network request in a 12s timeout so network hangs NEVER freeze processingRef!
        const data = await withTimeout(fetchChatText(cmd), 12000);
        const reply = data.reply?.trim() || 'At your service, Boss.';
        const action = data.action?.trim() || 'none';

        if (action && action !== 'none') {
          onCommandRef.current?.(action);
        }

        onConversationRef.current?.({
          transcript: cmd,
          reply,
          action,
        });

        // Mark speaking active while TTS audio plays to suppress mic self-echo
        isSpeakingRef.current = true;
        speak(reply)
          .catch((e) => console.warn('[Voice] TTS speak error:', e))
          .finally(() => {
            // Short delay after speaking finishes to let audio reverberation clear
            setTimeout(() => {
              isSpeakingRef.current = false;
            }, 400);
          });
      } catch (err) {
        console.warn('[Voice] Command error:', err);
      } finally {
        processingRef.current = false;
      }
    };

    const timer = setTimeout(start, 0);

    return () => {
      cancelled = true;
      activeRef.current = false;
      if (keepAliveTimer) clearInterval(keepAliveTimer);
      if (restartTimer) clearTimeout(restartTimer);
      try { rec?.abort(); } catch (_) {}
      clearTimeout(timer);
    };
  }, []);
}