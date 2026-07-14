import { useState, useEffect } from 'react';

// Returns a scale factor so the fixed-size HUD/lock content fits smaller
// windows without overflowing or clipping. Designed against a 1280x800 baseline.
export function useFitScale() {
    const [scale, setScale] = useState(1);

    useEffect(() => {
        const calc = () => {
            const s = Math.min(window.innerWidth / 1280, window.innerHeight / 800);
            setScale(Math.max(0.55, Math.min(1.15, s)));
        };
        calc();
        window.addEventListener('resize', calc);
        return () => window.removeEventListener('resize', calc);
    }, []);

    return scale;
}
