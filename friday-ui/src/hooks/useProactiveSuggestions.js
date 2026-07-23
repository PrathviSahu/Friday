/**
 * useProactiveSuggestions
 *
 * Polls /api/proactive every 30 minutes (and once after 10s on mount).
 * When FRIDAY has something useful to say, it:
 *   1. Calls onSuggestion({ message, action }) so the UI can display a toast.
 *   2. Speaks the suggestion via TTS.
 *   3. Does NOT fire the action automatically — instead it calls onPendingAction(action)
 *      so the caller can wait for a "yes" confirmation before executing it.
 *
 * To confirm a pending action, call confirmPendingAction() from outside.
 * The pending action expires after 60 seconds if not confirmed.
 */
import { useEffect, useRef, useCallback } from 'react';
import { speak } from '../services/ttsService';
import { fetchChatText } from '../api/chatText';

const PROACTIVE_INTERVAL_MS = 30 * 60 * 1000; // 30 minutes
const INITIAL_DELAY_MS       = 10 * 1000;      // 10 seconds after mount
const PENDING_EXPIRY_MS      = 60 * 1000;      // pending action expires after 60s

export function useProactiveSuggestions({ enabled = true, onSuggestion, onPendingAction }) {
  const enabledRef         = useRef(enabled);
  const onSuggestionRef    = useRef(onSuggestion);
  const onPendingActionRef = useRef(onPendingAction);
  const pendingActionRef   = useRef(null);   // { action, expiresAt }
  const pendingTimerRef    = useRef(null);

  useEffect(() => { enabledRef.current = enabled; }, [enabled]);
  useEffect(() => { onSuggestionRef.current = onSuggestion; }, [onSuggestion]);
  useEffect(() => { onPendingActionRef.current = onPendingAction; }, [onPendingAction]);

  // Call this when user says "yes" / "yeah" / "sure" etc.
  const confirmPendingAction = useCallback(async () => {
    const pending = pendingActionRef.current;
    if (!pending) return false;
    if (Date.now() > pending.expiresAt) {
      pendingActionRef.current = null;
      onPendingActionRef.current?.(null);
      return false;
    }
    // Clear the pending action before executing so double-yes doesn't re-fire
    pendingActionRef.current = null;
    if (pendingTimerRef.current) {
      clearTimeout(pendingTimerRef.current);
      pendingTimerRef.current = null;
    }
    onPendingActionRef.current?.(null);
    console.log('[Proactive] User confirmed — executing action:', pending.action);
    try { await fetchChatText(pending.action, true); } catch (_) {}
    return true;
  }, []);

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

        // If there's an action, hold it as PENDING — do NOT fire automatically
        if (data.action && data.action !== 'none') {
          const expiresAt = Date.now() + PENDING_EXPIRY_MS;
          pendingActionRef.current = { action: data.action, expiresAt };
          onPendingActionRef.current?.(data.action);
          console.log('[Proactive] Action pending user confirmation:', data.action, '(expires in 60s)');

          // Auto-clear pending after expiry
          if (pendingTimerRef.current) clearTimeout(pendingTimerRef.current);
          pendingTimerRef.current = setTimeout(() => {
            if (pendingActionRef.current) {
              console.log('[Proactive] Pending action expired without confirmation.');
              pendingActionRef.current = null;
              onPendingActionRef.current?.(null);
            }
          }, PENDING_EXPIRY_MS);
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
      if (pendingTimerRef.current) clearTimeout(pendingTimerRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { confirmPendingAction };
}
