import { createContext, useContext, useEffect, useState } from 'react';

const FridayContext = createContext();

export function FridayProvider({ children }) {
  const [state, setState] = useState('idle');
  const [micEnabled, setMicEnabled] = useState(true);
  const [showDebug, setShowDebug] = useState(false);

  // Push-to-talk mode: mic only opens while Space / Button is held.
  // On mobile (Android/iOS), defaults to PTT so browser does not lock Android system audio.
  const [pttMode, setPttMode] = useState(() => {
    try {
      const saved = localStorage.getItem('friday_ptt_mode');
      if (saved !== null) return saved === '1';
      const isMobile = typeof window !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
      return isMobile;
    } catch (_) {
      return false;
    }
  });
  useEffect(() => {
    try { localStorage.setItem('friday_ptt_mode', pttMode ? '1' : '0'); } catch (_) {}
  }, [pttMode]);

  return (
    <FridayContext.Provider value={{ state, setState, micEnabled, setMicEnabled, showDebug, setShowDebug, pttMode, setPttMode }}>
      {children}
    </FridayContext.Provider>
  );
}

export function useFriday() {
  return useContext(FridayContext);
}

export default FridayContext;
