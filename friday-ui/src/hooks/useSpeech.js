import { useEffect, useRef } from 'react';
import { matchVoiceCommand } from './voiceCommands';

/**
 * Web Speech API hook.
 * Starts speech recognition once and restarts it only when the browser allows it.
 */
export function useSpeech({ onCommand, onTranscript, enabled = false }) {
    const recognitionRef = useRef(null);
    const activeRef = useRef(false);
    const lastStartRef = useRef(0);
    const restartTimerRef = useRef(null);
    const isListeningRef = useRef(false);
    const isStartingRef = useRef(false);

    // Keep the latest callbacks in refs so the recognition lifecycle (below)
    // does NOT have to be torn down/recreated every time the caller's
    // onCommand/onTranscript identities change. Recreating SpeechRecognition
    // mid-conversation is what was dropping the 2nd (and later) commands.
    const onCommandRef = useRef(onCommand);
    const onTranscriptRef = useRef(onTranscript);
    onCommandRef.current = onCommand;
    onTranscriptRef.current = onTranscript;

    useEffect(() => {
        const SpeechRecognition =
            window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            console.warn('F.R.I.D.A.Y.: SpeechRecognition not supported in this browser.');
            return;
        }

        const mapCommand = (transcript) => matchVoiceCommand(transcript);

        const clearRestartTimer = () => {
            if (restartTimerRef.current) {
                clearTimeout(restartTimerRef.current);
                restartTimerRef.current = null;
            }
        };

        const stop = () => {
            clearRestartTimer();
            isStartingRef.current = false;
            isListeningRef.current = false;
            if (recognitionRef.current) {
                try { recognitionRef.current.stop(); } catch (e) {}
                recognitionRef.current = null;
            }
        };

        const ensureRecognition = () => {
            if (recognitionRef.current) return recognitionRef.current;

            const rec = new SpeechRecognition();
            rec.continuous = true;
            rec.interimResults = true;
            rec.lang = 'en-US';
            rec.maxAlternatives = 1;

            rec.onstart = () => {
                isStartingRef.current = false;
                isListeningRef.current = true;
                console.log('F.R.I.D.A.Y. speech recognition started');
            };

            rec.onresult = (event) => {
                let transcript = '';
                for (let i = event.resultIndex; i < event.results.length; i += 1) {
                    const result = event.results[i];
                    if (!result.isFinal) continue;
                    transcript = `${transcript}${result[0]?.transcript || ''}`.trim();
                    if (i < event.results.length - 1) transcript += ' ';
                }

                if (!transcript) return;

                console.log('F.R.I.D.A.Y. Heard:', transcript);
                // If the passphrase handler consumes this utterance (e.g. unlock
                // or lock), don't also run a general voice command like "wake".
                const consumed = onTranscriptRef.current?.(transcript);
                if (consumed) return;
                const command = mapCommand(transcript);
                if (command) {
                    console.log('F.R.I.D.A.Y. Command:', command);
                    clearRestartTimer();
                    onCommandRef.current?.(command);
                }
            };

            rec.onend = () => {
                isListeningRef.current = false;
                isStartingRef.current = false;
                if (!activeRef.current || (typeof document !== 'undefined' && document.hidden)) {
                    return;
                }
                console.log('F.R.I.D.A.Y. recognition ended — restarting listener');
                scheduleRestart(150);
            };

            rec.onerror = (event) => {
                const error = event.error || 'unknown';
                isStartingRef.current = false;
                isListeningRef.current = false;
                console.warn('F.R.I.D.A.Y. recognition error', error);
                // Only permanent failures (permission / no mic) should stop us.
                // Transient ones (aborted, no-speech, network) must keep listening.
                const fatal = ['not-allowed', 'service-not-allowed', 'audio-capture'];
                if (fatal.includes(error)) {
                    clearRestartTimer();
                    return;
                }
                scheduleRestart(300);
            };

            recognitionRef.current = rec;
            return rec;
        };

        const scheduleRestart = (delay = 600) => {
            clearRestartTimer();
            if (!activeRef.current || isStartingRef.current || isListeningRef.current) return;
            restartTimerRef.current = setTimeout(() => {
                restartTimerRef.current = null;
                start();
            }, delay);
        };

        const start = () => {
            if (!enabled || !activeRef.current) return;
            if (isStartingRef.current || isListeningRef.current) return;
            if (typeof document !== 'undefined' && document.hidden) return;

            const now = Date.now();
            if (now - lastStartRef.current < 400) {
                scheduleRestart(500);
                return;
            }
            lastStartRef.current = now;
            isStartingRef.current = true;

            const rec = ensureRecognition();
            try {
                rec.start();
            } catch (error) {
                isStartingRef.current = false;
                isListeningRef.current = false;
                console.warn('F.R.I.D.A.Y. recognition failed to start', error);
                if (activeRef.current) scheduleRestart(1000);
            }
        };

        activeRef.current = enabled;
        clearRestartTimer();
        if (enabled) start();
        else stop();

        // Expose debug helpers for runtime inspection and manual control
        if (typeof window !== 'undefined') {
            window.fridaySpeechInfo = () => ({
                hasRecognition: !!recognitionRef.current,
                isListening: !!isListeningRef.current,
                isStarting: !!isStartingRef.current,
                enabled: !!enabled,
                active: !!activeRef.current,
            });
            window.fridaySpeechStart = () => { activeRef.current = true; start(); };
            window.fridaySpeechStop = () => { activeRef.current = false; stop(); };
        }

        return () => {
            activeRef.current = false;
            clearRestartTimer();
            stop();
            try { if (typeof window !== 'undefined') {
                delete window.fridaySpeechInfo;
                delete window.fridaySpeechStart;
                delete window.fridaySpeechStop;
            } } catch (e) {}
        };
    }, [enabled]);
}
