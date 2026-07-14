import { useRef, useEffect } from 'react';

export function useMouse() {
    const mouse = useRef({ x: 0, y: 0, dx: 0, dy: 0 });

    useEffect(() => {
        const onMove = (e) => {
            mouse.current.dx = e.clientX / window.innerWidth  - 0.5;
            mouse.current.dy = e.clientY / window.innerHeight - 0.5;
        };
        window.addEventListener('mousemove', onMove);
        return () => window.removeEventListener('mousemove', onMove);
    }, []);

    return mouse;
}
