import { useEffect, useRef } from 'react';
import { useFriday } from './FridayContext';
import { useOrbState } from '../hooks/useOrbState';

// Sync the simple FridayContext string states to the more elaborate OrbProvider states
export default function FridaySync() {
    const { state: fridayState, micEnabled } = useFriday();
    const { transitionTo, start: startMic, stop: stopMic } = useOrbState();
    const isMicStarted = useRef(false);

    // Map context states to Orb states
    useEffect(() => {
        const map = {
            idle: 'IDLE',
            listening: 'LISTENING',
            thinking: 'THINKING',
            speaking: 'THINKING',
            verified: 'UNLOCKED',
            alert: 'BOOTING',
        };
        const target = map[fridayState] || 'IDLE';
        transitionTo?.(target);
    }, [fridayState, transitionTo]);

    // Manage microphone start/stop based on micEnabled flag
    useEffect(() => {
        if (micEnabled && !isMicStarted.current) {
            startMic();
            isMicStarted.current = true;
        } else if (!micEnabled && isMicStarted.current) {
            stopMic();
            isMicStarted.current = false;
        }
    }, [micEnabled, startMic, stopMic]);

    return null;
}
