import React, { useRef, useEffect } from 'react';
import './Waveform.css';
import { useOrbState } from '../../hooks/useOrbState';

export default function Waveform({ bars = 24 }) {
  const canvasRef = useRef(null);
  const rafRef = useRef(null);
  const { appState, audioLevelRef } = useOrbState();
  const state = ({ BOOTING: 'alert', IDLE: 'idle', LISTENING: 'listening', THINKING: 'thinking', VERIFYING: 'thinking', UNLOCKED: 'verified' }[appState]) || 'idle';

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    function render() {
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);

      const barWidth = width / bars;
      const t = Date.now() / 1000;

      for (let i = 0; i < bars; i++) {
        // prefer real mic level if provided by orb provider
        const base = audioLevelRef && audioLevelRef.current ? audioLevelRef.current : (0.06 + 0.04 * Math.sin(t * 2.5 + i * 0.2));
        // amplify when listening/speaking
        let amp = base * (state === 'listening' ? 3.5 : state === 'speaking' ? 4.2 : 1.0);
        amp = Math.min(1.0, amp + (Math.sin(t * 3 + i) * 0.02));
        const barH = Math.max(2, amp * height * 0.9);
        const x = i * barWidth + 1;
        const y = (height - barH) / 2;
        ctx.fillStyle = 'rgba(0,183,255,0.95)';
        ctx.fillRect(x, y, barWidth - 2, barH);
      }

      rafRef.current = requestAnimationFrame(render);
    }

    rafRef.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(rafRef.current);
  }, [audioLevelRef, bars, state]);

  return (
    <div className={`waveform waveform-${state}`} aria-hidden>
      <canvas ref={canvasRef} width={240} height={30} />
    </div>
  );
}
