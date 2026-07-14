import { createContext, useContext, useState } from 'react';

const FridayContext = createContext();

export function FridayProvider({ children }) {
  const [state, setState] = useState('idle');
  const [micEnabled, setMicEnabled] = useState(false);
  const [showDebug, setShowDebug] = useState(false);
  return (
    <FridayContext.Provider value={{ state, setState, micEnabled, setMicEnabled, showDebug, setShowDebug }}>
      {children}
    </FridayContext.Provider>
  );
}

export function useFriday() {
  return useContext(FridayContext);
}

export default FridayContext;
