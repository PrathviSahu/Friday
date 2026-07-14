import { useState } from 'react';

export default function ForcePlayButton() {
  const [status, setStatus] = useState('idle');

  const playDebug = async () => {
    setStatus('loading');
    try {
      const response = await fetch('/api/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: 'This is a backend audio verification test.' }),
      });
      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }
      const payload = await response.json();
      const audioUrl = payload.url.startsWith('/') ? `${window.location.origin}${payload.url}` : payload.url;
      const audio = new Audio(audioUrl);
      audio.crossOrigin = 'anonymous';
      await audio.play();
      setStatus('played');
      audio.onended = () => setStatus('idle');
    } catch (error) {
      console.error('Force play failed', error);
      setStatus('error');
    }
  };

  return (
    <button
      onClick={playDebug}
      className="fixed bottom-6 left-6 z-50 rounded-full bg-[#00B7FF] px-4 py-3 text-[11px] font-bold uppercase tracking-[0.35em] text-[#001018] shadow-lg"
      style={{ pointerEvents: 'auto' }}
    >
      {status === 'loading' ? 'Loading...' : status === 'error' ? 'Play Failed' : 'Force Play Audio'}
    </button>
  );
}
