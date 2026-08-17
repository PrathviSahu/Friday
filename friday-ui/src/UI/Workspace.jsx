import { AnimatePresence } from 'framer-motion';
import { Suspense, lazy } from 'react';
import { useOrbState } from '../hooks/useOrbState';

// Both workspaces are lazy-loaded so the trading bundle (lightweight-charts,
// WebGL) doesn't bloat the main chunk until it's actually opened.
const QuantumTradingWorkstation = lazy(() =>
  import('./TradingWorkstation/QuantumTradingWorkstation.jsx'));
const CareerOS = lazy(() => import('./Career/CareerOS.jsx'));

const FALLBACK = (
  <div style={{
    position: 'fixed', inset: 0, background: '#080B14',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 100, fontFamily: 'Inter, system-ui, sans-serif',
  }}>
    <div style={{ textAlign: 'center', color: '#475569' }}>
      <div style={{ fontSize: 13, marginBottom: 8 }}>Loading…</div>
      <div style={{ width: 160, height: 2, background: 'rgba(255,255,255,0.06)', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{ width: '60%', height: '100%', background: '#6366f1', borderRadius: 99, animation: 'shimmerLoad 1s ease infinite alternate' }} />
      </div>
    </div>
  </div>
);

// Overlays the active workspace panel on top of the ambient LockScreen
// (Background + orb) based on the `workspace` state driven by voice commands.
export default function Workspace() {
    const { workspace, setWorkspace } = useOrbState();

    const isTradingActive = workspace === 'trading' || workspace === 'trading_minimized';
    const isCareerActive  = workspace === 'career';

    if (!isTradingActive && !isCareerActive) return null;

    return (
        <div className="absolute inset-0" style={{ zIndex: 40, pointerEvents: 'auto' }}>
            <AnimatePresence mode="wait">
                {isTradingActive && (
                    <Suspense fallback={FALLBACK}>
                        <QuantumTradingWorkstation
                            key="trading_persisted"
                            isMinimized={workspace === 'trading_minimized'}
                            onMinimize={() => setWorkspace('trading_minimized')}
                            onRestore={() => setWorkspace('trading')}
                            onClose={() => setWorkspace('unlocked')}
                        />
                    </Suspense>
                )}
            </AnimatePresence>

            {/* Career OS — mounts as full-screen overlay, persists state while open */}
            {isCareerActive && (
                <Suspense fallback={FALLBACK}>
                    <CareerOS onClose={() => setWorkspace('unlocked')} />
                </Suspense>
            )}
        </div>
    );
}
