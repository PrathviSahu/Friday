import { useEffect, useRef } from 'react';
import { matchVoiceCommand } from './voiceCommands';
import { speak } from '../services/ttsService';
import { fetchChatText } from '../api/chatText';

/**
 * Wake word trigger phrases.
 */
const WAKE_WORDS = [
  'hey friday',
  'hi friday',
  'hello friday',
  'ok friday',
  'okay friday',
  'wake up friday',
  'wake up',
  'friday',
  'hey',
  'hi',
  'hello',
  'ok',
  'okay'
];

/**
 * Returns the command part after the wake-word found.
 */
function extractCommand(transcript) {
  if (!transcript) return null;
  const t = transcript.trim().toLowerCase();

  const sortedWords = WAKE_WORDS.slice().sort((a, b) => b.length - a.length);

  for (const wakeWord of sortedWords) {
    const index = t.indexOf(wakeWord);
    if (index !== -1) {
      const after = t.substring(index + wakeWord.length).replace(/^[\s,.\-?]+/, '').trim();
      return after || 'hello';
    }
  }

  return null;
}

export function useSpeech({ onCommand, onConversation, enabled = false, locked = true }) {
  const activeRef = useRef(false);
  const processingRef = useRef(false);

  const onCommandRef = useRef(onCommand);
  const onConversationRef = useRef(onConversation);
  const lockedRef = useRef(locked);

  onCommandRef.current = onCommand;
  onConversationRef.current = onConversation;
  lockedRef.current = locked;

  useEffect(() => {
    if (!enabled) return;

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      console.warn('[Voice] SpeechRecognition not available in this browser.');
      return;
    }

    let cancelled = false;
    let rec = null;

    const start = async () => {
      if (cancelled) return;

      try {
        await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (e) {
        console.warn('[Voice] Mic permission denied:', e);
        return;
      }

      rec = new SR();
      rec.continuous = true;
      rec.interimResults = false;
      rec.lang = 'en-US';

      rec.onresult = (e) => {
        const result = e.results[e.resultIndex];
        if (!result || !result.isFinal) return;
        const text = result[0].transcript.trim();
        if (!text) return;

        console.log('[Voice] Speech recognized:', text);
        const cmd = extractCommand(text);
        if (cmd) {
          console.log('[Voice] Wake-word matched! Processing command:', cmd);
          handleCmd(cmd);
        } else {
          console.log('[Voice] No wake-word detected in:', text);
        }
      };

      rec.onerror = (e) => {
        console.warn('[Voice] Recognition error:', e.error || e);
        if (!cancelled && activeRef.current) {
          setTimeout(start, 300);
        }
      };

      rec.onend = () => {
        if (!cancelled && activeRef.current && enabled) {
          setTimeout(start, 100);
        }
      };

      try {
        rec.start();
        activeRef.current = true;
        console.log('[Voice] Started listening for wake words...');
      } catch (e) {
        console.warn('[Voice] Could not start recognition:', e);
      }
    };

    const handleCmd = async (cmd) => {
      if (processingRef.current) return;

      processingRef.current = true;
      try {
        // SECURITY CHECK: If system is LOCKED, FRIDAY only responds with security greeting/warning
        if (lockedRef.current) {
          const lockedReply = "Access denied, Boss. Please authenticate with your fingerprint or biometric key first to access system functions.";
          console.log('[Voice] System is locked. Refusing main commands.');
          
          onConversationRef.current?.({
            transcript: cmd,
            reply: lockedReply,
            action: 'none',
          });

          await speak(lockedReply);
          return;
        }

        // UNLOCKED STATE: Process main functions (Trading, Dashboard, Job Search, etc.)
        const localCommand = matchVoiceCommand(cmd);
        if (localCommand) {
          console.log('[Voice] Local command matched:', localCommand);
          onCommandRef.current?.(localCommand);
          processingRef.current = false;
          return;
        }

        console.log('[Voice] Sending query to FRIDAY AI:', cmd);
        const data = await fetchChatText(cmd);
        const reply = data.reply?.trim() || '';
        const action = data.action?.trim() || 'none';

        console.log('[Voice] FRIDAY response:', { reply, action });

        if (action && action !== 'none') {
          onCommandRef.current?.(action);
        }

        onConversationRef.current?.({
          transcript: cmd,
          reply,
          action,
        });

        await speak(reply);
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
  }, [enabled]);
}