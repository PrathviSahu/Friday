import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import './OrbDebug.css';
import { useFriday } from '../../context/FridayContext';

export default function OrbDebug(){
  const { state, setState, showDebug, setShowDebug } = useFriday();
  const states = ['idle','listening','thinking','speaking','verified','alert'];

  return (
    <AnimatePresence>
      {showDebug && (
        <motion.div
          className="orb-debug-panel"
          initial={{ x: -360, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: -360, opacity: 0 }}
          transition={{ duration: 0.26, ease: [0.2, 0.9, 0.2, 1] }}
        >
          <div className="orb-debug">
            <div className="orb-debug-header">
              ORB DEBUG
              <button className="orb-debug-close" onClick={() => setShowDebug(false)} aria-label="Close debug panel">×</button>
            </div>
            <div className="orb-debug-state">state: <strong>{state}</strong></div>
            <div className="orb-debug-buttons">
              {states.map(s => (
                <button key={s} onClick={() => setState(s)} className={s === state ? 'active' : ''}>{s}</button>
              ))}
            </div>
            <div className="orb-debug-actions">
              <button onClick={() => { console.log('fridayState', state); alert('fridayState: ' + state); }}>check</button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
