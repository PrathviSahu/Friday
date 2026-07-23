import { AnimatePresence } from 'framer-motion';
import { useOrbState } from '../hooks/useOrbState';
import Dashboard from './Dashboard/Dashboard';
import QuantumTradingWorkstation from './TradingWorkstation/QuantumTradingWorkstation';

// Overlays the active workspace panel on top of the ambient LockScreen
// (Background + orb) based on the `workspace` state driven by voice commands.
export default function Workspace() {
    const { workspace, setWorkspace } = useOrbState();

    if (workspace === 'lockscreen') return null;

    const isTradingActive = workspace === 'trading' || workspace === 'trading_minimized';

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
                {workspace === 'dashboard' && (
                    <Dashboard key="dashboard" onLock={() => setWorkspace('lockscreen')} />
                )}
            </AnimatePresence>
        </div>
    );
}
