import { AnimatePresence } from 'framer-motion';
import { Suspense, lazy } from 'react';
import { useOrbState } from '../hooks/useOrbState';
import QuantumTradingWorkstation from './TradingWorkstation/QuantumTradingWorkstation';

// Career OS (Job Portal) is lazy-loaded so it doesn't bloat the main bundle
const CareerOS = lazy(() => import('./Career/CareerOS.jsx'));

// Overlays the active workspace panel on top of the ambient LockScreen
// (Background + orb) based on the `workspace` state driven by voice commands.
export default function Workspace() {
    const { workspace, setWorkspace } = useOrbState();

    if (workspace === 'lockscreen') return null;

    const isTradingActive = workspace === 'trading' || workspace === 'trading_minimized';
    const isCareerActive  = workspace === 'career' || workspace === 'dashboard';

    return (
        <div className="absolute inset-0" style={{ zIndex: 40, pointerEvents: 'auto' }}>
            <AnimatePresence mode="wait">
                {isTradingActive && (
                    <QuantumTradingWorkstation
                        key="trading_persisted"
                        isMinimized={workspace === 'trading_minimized'}
                        onMinimize={() => setWorkspace('trading_minimized')}
                        onRestore={() => setWorkspace('trading')}
                        onClose={() => setWorkspace('unlocked')}
                    />
                )}
            </AnimatePresence>

            {/* Career OS — mounts as full-screen overlay, persists state while open */}
            {isCareerActive && (
                <Suspense fallback={
                    <div style={{
                        position: 'fixed', inset: 0, background: '#080B14',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        zIndex: 100, fontFamily: 'Inter, system-ui, sans-serif',
                    }}>
                        <div style={{ textAlign: 'center', color: '#475569' }}>
                            <div style={{ fontSize: 13, marginBottom: 8 }}>Loading Career OS…</div>
                            <div style={{ width: 160, height: 2, background: 'rgba(255,255,255,0.06)', borderRadius: 99, overflow: 'hidden' }}>
                                <div style={{ width: '60%', height: '100%', background: '#6366f1', borderRadius: 99, animation: 'shimmerLoad 1s ease infinite alternate' }} />
                            </div>
                        </div>
                    </div>
                }>
                    <CareerOS onClose={() => setWorkspace('unlocked')} />
                </Suspense>
            )}
        </div>
    );
}
