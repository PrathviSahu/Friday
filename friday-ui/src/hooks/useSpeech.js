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
          setTimeout(start, 250);
        }
      };

      rec.onend = () => {
        console.log('[Voice] Recognition ended, auto-restarting...');
        activeRef.current = false;
        if (!cancelled) {
          setTimeout(start, 200);
        }
      };

      rec.onresult = (e) => {
        // FIX: Extract result from current event turn rather than accumulated results array length
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
        setTimeout(start, 300);
      }
    };

    // Watchdog keep-alive loop (checks activeRef and forces restart if Chrome drops listener)
    keepAliveTimer = setInterval(() => {
      if (!cancelled && !activeRef.current && !processingRef.current) {
        console.log('[Voice Watchdog] Mic inactive, auto-restarting listener...');
        start();
      }
    }, 2000);

    const handleCmd = async (cmd) => {
      // Allow rapid command processing without getting stuck
      processingRef.current = true;
      try {
        if (lockedRef.current) {
          const lockedReply = "Access denied, Boss. Please authenticate with your fingerprint key first.";
          onConversationRef.current?.({ transcript: cmd, reply: lockedReply, action: 'none' });
          await speak(lockedReply);
          return;
        }

        const localCommand = matchVoiceCommand(cmd);
        if (localCommand) {
          onCommandRef.current?.(localCommand);
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

        speak(reply).catch((e) => console.warn('[Voice] TTS speak error:', e));
      } catch (err) {
        console.warn('[Voice] Command error:', err);
      } finally {
        // Guarantee processing flag always resets immediately
        processingRef.current = false;
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