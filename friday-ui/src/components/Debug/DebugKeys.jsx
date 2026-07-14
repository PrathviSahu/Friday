import { useEffect } from 'react';
import { useFriday } from '../../context/FridayContext';

export default function DebugKeys() {
    const { setState, setMicEnabled, setShowDebug } = useFriday();
    useEffect(() => {
        const handler = (e) => {
            // Toggle debug panel with F9
            if (e.code === 'F9' || e.key === 'F9') {
                setShowDebug((current) => !current);
                e.preventDefault();
                return;
            }
            if (e.code === 'Space' || e.key === ' ') {
                setMicEnabled((previous) => {
                    const next = !previous;
                    setState(next ? 'listening' : 'idle');
                    return next;
                });
                e.preventDefault();
                return;
            }

            switch(e.key){
                case '1':
                    setState('idle');
                    break;
                case '2':
                    setState('listening');
                    break;
                case '3':
                    setState('thinking');
                    break;
                case '4':
                    setState('speaking');
                    break;
                case '5':
                    setState('verified');
                    break;
                default:
                    break;
            }
        };
        window.addEventListener('keydown',handler);
        return ()=>window.removeEventListener('keydown',handler);
    },[setState, setMicEnabled, setShowDebug]);
    return null;
}
