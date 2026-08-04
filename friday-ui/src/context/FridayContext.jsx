import { createContext, useContext, useEffect, useState } from 'react';

const FridayContext = createContext();

export function FridayProvider({ children }) {
  const [state, setState] = useState('idle');
  const [micEnabled, setMicEnabled] = useState(true);
  const [showDebug, setShowDebug] = useState(false);

  // Push-to-talk mode: mic only opens while Space is held (instead of
  // always-on listening). Remembered across reloads.
  const [pttMode, setPttMode] = useState(() => {
    try { return localStorage.getItem('friday_ptt_mode') === '1'; } catch (_) { return false; }
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
