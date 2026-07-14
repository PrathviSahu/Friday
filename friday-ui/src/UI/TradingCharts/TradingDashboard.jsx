import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import TradingViewPanel from './TradingViewPanel';
import Watchlist from './Watchlist';
import TickerTape from './TickerTape';
import AlertsPanel from './AlertsPanel';
import { useWatchlist } from './useWatchlist';
import { fetchQuotes, formatSymbol, INTERVALS } from '../../services/market';
import { useOrbState } from '../../hooks/useOrbState';

const DRAW_TOOLS = [
    { id: null, label: 'Select' },
    { id: 'trend', label: 'Trend' },
    { id: 'hline', label: 'Horizontal Line' },
    { id: 'ray', label: 'Ray' },
    { id: 'rect', label: 'Rectangle' },
];

const ALERTS_KEY = 'friday_alerts';

function loadAlerts() {
    try {
        const raw = localStorage.getItem(ALERTS_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

export default function TradingDashboard({ onClose }) {
    const { speakText, audioEnabled } = useOrbState();
    const { symbols, add, remove } = useWatchlist();

    const [selected, setSelected] = useState('RELIANCE.NS');
    const [interval, setInterval] = useState('5m');
    const [quotes, setQuotes] = useState({});
    const [drawMode, setDrawMode] = useState(null);
    const [clearSignal, setClearSignal] = useState(0);
    const [alertsOpen, setAlertsOpen] = useState(false);
    const [alerts, setAlerts] = useState(loadAlerts);
    const [toast, setToast] = useState(null);

    const selectedQuote = quotes[selected];

    // ── live quote polling ──────────────────────────────────────────────────
    useEffect(() => {
        let cancelled = false;
        const poll = async () => {
            if (!symbols.length) return;
            try {
                const list = await fetchQuotes(symbols);
                if (cancelled) return;
                const map = {};
                for (const q of list) map[q.symbol] = q;
                setQuotes((prev) => ({ ...prev, ...map }));
                checkAlerts(map);
            } catch {
                /* backend/Yahoo hiccup — keep last quotes */
            }
        };
        poll();
        const id = setInterval(poll, 6000);
        return () => {
            cancelled = true;
            clearInterval(id);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [symbols.join(',')]);

    // ── alerts: persist + monitor ─────────────────────────────────────────────
    useEffect(() => {
        try {
            localStorage.setItem(ALERTS_KEY, JSON.stringify(alerts));
        } catch {
            /* ignore */
        }
    }, [alerts]);

    const checkAlerts = useCallback(
        (quoteMap) => {
            setAlerts((prev) => {
                let changed = false;
                const next = prev.map((a) => {
                    if (a.triggered) return a;
                    const q = quoteMap[a.symbol];
                    if (!q || q.price == null) return a;
                    const hit = a.direction === 'above' ? q.price >= a.price : q.price <= a.price;
                    if (hit) {
                        changed = true;
                        const msg = `Boss, ${formatSymbol(a.symbol)} crossed ${a.price}.`;
                        setToast({ symbol: a.symbol, msg });
                        if (audioEnabled) speakText(msg);
                        return { ...a, triggered: true };
                    }
                    return a;
                });
                return changed ? next : prev;
            });
        },
        [audioEnabled, speakText],
    );

    const createAlert = (alert) => {
        const maxAlerts = 10; // Prevent too many alerts
        if (alerts.length >= maxAlerts) {
            return; // Silent ignore
        }
        setAlerts((prev) => [...prev, { ...alert, id: `al_${Date.now()}`, triggered: false }]);
    };

    const deleteAlert = (id) => setAlerts((prev) => prev.filter((a) => a.id !== id));
    const clearTriggered = () => setAlerts((prev) => prev.filter((a) => !a.triggered));

    const livePrice = selectedQuote?.price ?? null;

    return (
        <motion.div
            className="absolute inset-0 flex flex-col bg-[#0b0e17]"
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.03 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
        >
            <TickerTape symbols={symbols} quotes={quotes} />

            <div className="flex flex-1 min-h-0">
                <Watchlist
                    symbols={symbols}
                    quotes={quotes}
                    selected={selected}
                    onSelect={setSelected}
                    onRemove={remove}
                    onAdd={add}
                />

                <div className="flex-1 min-w-0 flex flex-col">
                    {/* Header */}
                    <div className="flex items-center justify-between px-5 py-3 border-b border-[#1e222d]">
                        <div className="flex items-baseline gap-3">
                            <span className="font-orbitron text-xl tracking-widest text-[#DFFAFF]">
                                {formatSymbol(selected)}
                            </span>
                            <span className="font-grotesk text-2xl text-[#DFFAFF]">
                                {selectedQuote?.price != null ? selectedQuote.price.toLocaleString() : '—'}
                            </span>
                            {selectedQuote?.changePercent != null && (
                                <span
                                    className={`font-grotesk text-sm ${
                                        selectedQuote.changePercent >= 0 ? 'text-[#26a69a]' : 'text-[#ef5350]'
                                    }`}
                                >
                                    {selectedQuote.changePercent >= 0 ? '+' : ''}
                                    {selectedQuote.changePercent.toFixed(2)}%
                                </span>
                            )}
                            <span className="text-[10px] tracking-[0.3em] uppercase text-[#00B7FF]/50">
                                {interval} • delayed
                            </span>
                        </div>
                        <button
                            onClick={onClose}
                            className="border border-[#ff4444]/30 bg-[#ff4444]/5 hover:bg-[#ff4444]/15 px-3 py-1.5 rounded text-[9px] font-orbitron tracking-widest text-[#ff6666] transition-all uppercase cursor-pointer"
                        >
                            ✕ Console [Back]
                        </button>
                    </div>

                    {/* Toolbar */}
                    <div className="flex items-center justify-between px-5 py-2 border-b border-[#1e222d]">
                        <div className="flex items-center gap-1">
                            {INTERVALS.map((iv) => (
                                <button
                                    key={iv}
                                    onClick={() => setInterval(iv)}
                                    className={`px-2.5 py-1 rounded text-[10px] tracking-[0.15em] uppercase transition ${
                                        interval === iv
                                            ? 'bg-[#00B7FF] text-[#001018] font-bold'
                                            : 'text-[#8b93a5] hover:text-[#DFFAFF] border border-[#1e222d]'
                                    }`}
                                >
                                    {iv}
                                </button>
                            ))}
                        </div>

                        <div className="flex items-center gap-1">
                            {DRAW_TOOLS.map((t) => (
                                <button
                                    key={t.label}
                                    onClick={() => setDrawMode(t.id)}
                                    className={`px-2.5 py-1 rounded text-[10px] tracking-[0.15em] uppercase transition ${
                                        drawMode === t.id
                                            ? 'bg-[#FFB454] text-[#001018] font-bold'
                                            : 'text-[#8b93a5] hover:text-[#DFFAFF] border border-[#1e222d]'
                                    }`}
                                >
                                    {t.label}
                                </button>
                            ))}
                            <button
                                onClick={() => setClearSignal((c) => c + 1)}
                                className="px-2.5 py-1 rounded text-[10px] tracking-[0.15em] uppercase text-[#ef5350] border border-[#ef5350]/30 hover:bg-[#ef5350]/10"
                            >
                                Clear
                            </button>
                            <button
                                onClick={() => setAlertsOpen(true)}
                                className="px-2.5 py-1 rounded text-[10px] tracking-[0.15em] uppercase text-[#00D9FF] border border-[#00B7FF]/30 hover:bg-[#00B7FF]/10"
                            >
                                Alerts
                                {alerts.length > 0 && (
                                    <span className="ml-1 text-[#FFB454]">{alerts.length}</span>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Chart */}
                    <div className="flex-1 min-h-0 relative">
                        <TradingViewPanel
                            symbol={selected}
                            interval={interval}
                            livePrice={livePrice}
                            drawMode={drawMode}
                            clearSignal={clearSignal}
                        />
                    </div>
                </div>
            </div>

            <AlertsPanel
                open={alertsOpen}
                onClose={() => setAlertsOpen(false)}
                alerts={alerts}
                selectedSymbol={selected}
                onCreate={createAlert}
                onDelete={deleteAlert}
                onClearTriggered={clearTriggered}
            />

            {/* Toast */}
            <AnimatePresence>
                {toast && (
                    <motion.div
                        initial={{ opacity: 0, y: -10, x: 20 }}
                        animate={{ opacity: 1, y: 0, x: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        onAnimationComplete={() => setTimeout(() => setToast(null), 4000)}
                        className="absolute top-20 right-6 z-50 rounded-lg border border-[#26a69a]/40 bg-[#001018]/95 px-4 py-3 shadow-[0_0_30px_rgba(38,166,154,0.25)]"
                    >
                        <div className="text-[9px] uppercase tracking-[0.3em] text-[#26a69a] mb-1">Alert Triggered</div>
                        <div className="font-grotesk text-[12px] text-[#DFFAFF]">{toast.msg}</div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
