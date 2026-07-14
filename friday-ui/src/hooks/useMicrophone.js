import { useEffect, useRef, useCallback } from 'react';

/**
 * Taps the microphone via Web Audio API.
 * Writes a live [0..1] audio level into audioLevelRef.current every frame.
 * Also provides a Float32Array waveformData ref (128 samples).
 */
export function useMicrophone() {
    const audioLevelRef  = useRef(0);
    const waveformRef    = useRef(new Float32Array(64).fill(0));
    const cleanupRef     = useRef(null);
    const permissionRequestedRef = useRef(false);

    const requestPermission = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(t => t.stop()); // immediate stop, we just wanted permission
            return true;
        } catch (err) {
            console.warn('Microphone permission request failed:', err);
            return false;
        }
    }, []);

    const start = useCallback(async () => {
        // If we haven't asked for permission yet, do so now (requires user gesture)
        if (!permissionRequestedRef.current) {
            const granted = await requestPermission();
            permissionRequestedRef.current = true;
            if (!granted) {
                console.warn('Microphone permission not granted');
                return false;
            }
        }

        try {
            const stream  = await navigator.mediaDevices.getUserMedia({ audio: true });
            const ctx     = new AudioContext();
            const source  = ctx.createMediaStreamSource(stream);
            const analyser = ctx.createAnalyser();
            analyser.fftSize = 256;
            analyser.smoothingTimeConstant = 0.8;
            source.connect(analyser);

            const buf = new Uint8Array(analyser.frequencyBinCount);
            let raf;

            const tick = () => {
                analyser.getByteFrequencyData(buf);
                let sum = 0;
                for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
                audioLevelRef.current = Math.min(Math.sqrt(sum / buf.length) / 128, 1);

                analyser.getByteTimeDomainData(buf);
                for (let i = 0; i < 64; i++) {
                    waveformRef.current[i] = (buf[i] / 128.0) - 1.0;
                }

                raf = requestAnimationFrame(tick);
            };
            tick();

            cleanupRef.current = () => {
                cancelAnimationFrame(raf);
                stream.getTracks().forEach(t => t.stop());
                ctx.close();
            };
            return true;
        } catch (err) {
            console.warn('F.R.I.D.A.Y.: Microphone access denied — using simulated audio.', err);
            return false;
        }
    }, [requestPermission]);

    const stop = useCallback(() => {
        cleanupRef.current?.();
        cleanupRef.current = null;
        audioLevelRef.current = 0;
        waveformRef.current.fill(0);
    }, []);

    useEffect(() => {
        return () => stop();
    }, [stop]);

    return { audioLevelRef, waveformRef, start, stop };
}
