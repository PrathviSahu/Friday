import { useEffect, useRef } from 'react';
import { matchVoiceCommand, normalizeTranscript } from './voiceCommands';
import { fetchChatText } from '../api/chatText';
import { speak } from '../services/ttsService';

export function useSpeech({ isLocked, onCommand, onConversation }) {
  const activeRef = useRef(false);
  const processingRef = useRef(false);
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

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.warn('[Voice] SpeechRecognition not supported in this browser environment');
      return;
    }

    const start = () => {
      if (cancelled) return;

      // Clean up existing instance before recreating
      if (rec) {
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
        // Auto-restart immediately on non-fatal errors
        if (!cancelled && (e.error === 'no-speech' || e.error === 'network' || e.error === 'aborted')) {
          setTimeout(start, 300);
        }
      };

      rec.onend = () => {
        console.log('[Voice] Recognition ended, auto-restarting...');
        activeRef.current = false;
        if (!cancelled) {
          setTimeout(start, 250);
        }
      };

      rec.onresult = (e) => {
        const lastIndex = e.results.length - 1;
        const rawTranscript = e.results[lastIndex][0].transcript;
        console.log('[Voice] Raw speech recognized:', rawTranscript);

        let query = rawTranscript.trim();
        // Comprehensive regex to strip wake-word variations cleanly
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
        // Auto-restart if browser blocked re-activation
        setTimeout(start, 500);
      }
    };

    // Watchdog keep-alive loop to ensure the mic NEVER stays dead
    keepAliveTimer = setInterval(() => {
      if (!cancelled && !activeRef.current && !processingRef.current) {
        console.log('[Voice Watchdog] Mic inactive, auto-restarting listener...');
        start();
      }
    }, 3000);

    const handleCmd = async (cmd) => {
      if (processingRef.current) return;

      processingRef.current = true;
      try {
        // SECURITY CHECK: If system is LOCKED, block main features
        if (lockedRef.current) {
          const lockedReply = "Access denied, Boss. Please authenticate with your fingerprint key first.";
          
          onConversationRef.current?.({
            transcript: cmd,
            reply: lockedReply,
            action: 'none',
          });

          await speak(lockedReply);
          return;
        }

        // UNLOCKED STATE: Execute full system features
        const localCommand = matchVoiceCommand(cmd);
        if (localCommand) {
          onCommandRef.current?.(localCommand);
          processingRef.current = false;
          return;
        }

        const data = await fetchChatText(cmd);
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

        // Speak non-blocking so speech recognition never gets stuck if TTS finishes
        speak(reply).catch((e) => console.warn('[Voice] TTS speak error:', e));
      } catch (err) {
        console.warn('[Voice] Command error:', err);
      } finally {
        // Reset processing state after a short safety delay
        setTimeout(() => {
          processingRef.current = false;
        }, 300);
      }
    };

    const timer = setTimeout(start, 0);

    return () => {
      cancelled = true;
      activeRef.current = false;
      if (keepAliveTimer) clearInterval(keepAliveTimer);
      try { rec?.abort(); } catch (_) {}
      clearTimeout(timer);
    };
  }, []);
}