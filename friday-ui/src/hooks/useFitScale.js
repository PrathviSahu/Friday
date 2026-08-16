import { useState, useEffect } from 'react';

// Returns a scale factor so the fixed-size HUD/lock content fits smaller
// windows without overflowing or clipping. Designed against a 1280x800 baseline.
export function useFitScale() {
    const [scale, setScale] = useState(1);

    useEffect(() => {
        const calc = () => {
            const wScale = window.innerWidth / 1280;
            const hScale = window.innerHeight / 850;
            const s = Math.min(wScale, hScale);
            setScale(Math.max(0.5, Math.min(1.0, s)));
        };
        calc();
        window.addEventListener('resize', calc);
        return () => window.removeEventListener('resize', calc);
    }, []);

    return scale;
}
