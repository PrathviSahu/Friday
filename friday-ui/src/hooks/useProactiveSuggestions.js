/**
 * useProactiveSuggestions
 *
 * Polls /api/proactive every 30 minutes (and once after 10s on mount).
 * When FRIDAY has something useful to say, it:
 *   1. Calls onSuggestion({ message, action }) so the UI can display a toast/notification.
 *   2. Speaks via TTS.
 *   3. Fires the action if any (e.g. play_krishna_playlist).
 */
import { useEffect, useRef } from 'react';
import { speak } from '../services/ttsService';
import { fetchChatText } from '../api/chatText';

const PROACTIVE_INTERVAL_MS = 30 * 60 * 1000; // 30 minutes
const INITIAL_DELAY_MS       = 10 * 1000;      // 10 seconds after mount

export function useProactiveSuggestions({ enabled = true, onSuggestion }) {
  const enabledRef      = useRef(enabled);
  const onSuggestionRef = useRef(onSuggestion);

  useEffect(() => { enabledRef.current = enabled; }, [enabled]);
  useEffect(() => { onSuggestionRef.current = onSuggestion; }, [onSuggestion]);

  useEffect(() => {
    let initialTimer = null;
    let intervalTimer = null;

    const check = async () => {
      if (!enabledRef.current) return;
      try {
        const res = await fetch('http://localhost:8000/api/proactive');
        if (!res.ok) return;
        const data = await res.json();

        if (!data.should_speak || !data.message) return;

        console.log('[Proactive] FRIDAY has something to say:', data.message);

        // Notify UI (toast / conversation panel)
        onSuggestionRef.current?.({ message: data.message, action: data.action });

        // Speak the suggestion
        try { await speak(data.message); } catch (_) {}

        // If action is a playlist command, trigger it silently
        if (data.action && data.action !== 'none') {
          try { await fetchChatText(data.action, true); } catch (_) {}
        }
      } catch (err) {
        console.warn('[Proactive] Check failed:', err);
      }
    };

    // First check fires after a short delay (not immediately on mount)
    initialTimer = setTimeout(check, INITIAL_DELAY_MS);

    // Then every 30 minutes
    intervalTimer = setInterval(check, PROACTIVE_INTERVAL_MS);

    return () => {
      clearTimeout(initialTimer);
      clearInterval(intervalTimer);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}
