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

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.warn('[Voice] SpeechRecognition not supported in this browser environment');
      return;
    }

    const start = () => {
      if (cancelled) return;
      rec = new SpeechRec();
      rec.continuous = true;
      rec.interimResults = false;
      rec.lang = 'en-US';

      rec.onstart = () => {
        console.log('[Voice] Started listening...');
      };

      rec.onerror = (e) => {
        console.warn('[Voice] Recognition error:', e.error);
        activeRef.current = false;
      };

      rec.onend = () => {
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
        query = query.replace(/^(hey friday|friday)\s*/i, '').trim();

        if (query.length > 0) {
          console.log('[Voice] Clean query sent to AI (wake-word removed):', query);
          handleCmd(query);
        }
      };

      try {
        rec.start();
        activeRef.current = true;
      } catch (e) {
        // ignore already started error
      }
    };

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
        const reply = data.reply?.trim() || 'I am standing by, Boss.';
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
        processingRef.current = false;
      }
    };

    const timer = setTimeout(start, 0);

    return () => {
      cancelled = true;
      activeRef.current = false;
      try { rec?.stop(); } catch (_) {}
      clearTimeout(timer);
    };
  }, []);
}