import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { formatSymbol } from '../../services/market';

export default function AlertsPanel({ open, onClose, alerts, selectedSymbol, onCreate, onDelete, onClearTriggered }) {
    const [symbol, setSymbol] = useState(selectedSymbol || '');
    const [direction, setDirection] = useState('above');
    const [price, setPrice] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!symbol || !price) {
            setError('Symbol and price required');
            return;
        }
        const p = parseFloat(price);
        if (isNaN(p) || p <= 0) {
            setError('Invalid price');
            return;
        }
        onCreate({
            symbol: symbol.trim().toUpperCase(),
            direction,
            price: p,
        });
        setPrice('');
        setError('');
    };

    const handleDelete = (id) => {
        onDelete(id);
    };

    const handleClear = () => {
        onClearTriggered();
    };

    return (
        <AnimatePresence>
            {open && (
                <motion.div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose}
                >
                    <motion.div
                        className="bg-[#001018]/95 rounded-2xl border border-[#00B7FF]/30 p-6 w-full max-w-md shadow-[0_0_40px_rgba(0,183,255,0.2)]"
                        initial={{ scale: 0.95, y: 20 }}
                        animate={{ scale: 1, y: 0 }}
                        exit={{ scale: 0.95, y: 20 }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <h3 className="font-orbitron text-sm uppercase tracking-[0.3em] text-[#00D9FF] mb-4">
                            Price Alerts
                        </h3>

                        <form onSubmit={handleSubmit} className="space-y-3 mb-4">
                            <div>
                                <label className="block text-[10px] text-[#00B7FF]/60 mb-1">Symbol</label>
                                <input
                                    type="text"
                                    value={symbol}
                                    onChange={(e) => setSymbol(e.target.value)}
                                    placeholder={selectedSymbol}
                                    className="w-full bg-[#131722] border border-[#1e222d] rounded px-2 py-1.5 text-[12px] text-[#DFFAFF] focus:border-[#00B7FF]/50"
                                />
                            </div>
                            <div className="flex gap-2">
                                <div className="flex-1">
                                    <label className="block text-[10px] text-[#00B7FF]/60 mb-1">When</label>
                                    <select
                                        value={direction}
                                        onChange={(e) => setDirection(e.target.value)}
                                        className="w-full bg-[#131722] border border-[#1e222d] rounded px-2 py-1.5 text-[12px] text-[#DFFAFF]"
                                    >
                                        <option value="above">Above</option>
                                        <option value="below">Below</option>
                                    </select>
                                </div>
                                <div className="flex-1">
                                    <label className="block text-[10px] text-[#00B7FF]/60 mb-1">Price</label>
                                    <input
                                        type="number"
                                        step="any"
                                        value={price}
                                        onChange={(e) => setPrice(e.target.value)}
                                        className="w-full bg-[#131722] border border-[#1e222d] rounded px-2 py-1.5 text-[12px] text-[#DFFAFF]"
                                    />
                                </div>
                            </div>
                            {error && <div className="text-[10px] text-[#ff6b81]">{error}</div>}
                            <button
                                type="submit"
                                className="w-full bg-[#00B7FF] text-[#001018] text-[11px] uppercase font-bold rounded py-1.5"
                            >
                                Add Alert
                            </button>
                        </form>

                        <div className="border-t border-[#1e222d] pt-3">
                            <h4 className="font-grotesk text-[10px] text-[#00B7FF]/60 mb-2">Active Alerts</h4>
                            <div className="max-h-48 overflow-y-auto space-y-1">
                                {alerts.length === 0 ? (
                                    <div className="text-[10px] text-[#8b93a5] py-2">No alerts set</div>
                                ) : (
                                    alerts.map((alert) => (
                                        <div
                                            key={alert.id}
                                            className={`flex items-center justify-between px-3 py-1.5 rounded border ${
                                                alert.triggered ? 'border-[#26a69a]/40 bg-[#26a69a]/5' : 'border-[#1e222d]'
                                            }`}
                                        >
                                            <div>
                                                <span className="font-grotesk text-[12px] text-[#DFFAFF]">
                                                    {formatSymbol(alert.symbol)}
                                                </span>
                                                <div className="text-[10px] text-[#8b93a5]">
                                                    {alert.direction} {alert.price}
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                {alert.triggered && (
                                                    <span className="text-[9px] text-[#26a69a] uppercase">Fired</span>
                                                )}
                                                <button
                                                    onClick={() => handleDelete(alert.id)}
                                                    className="text-[#8b93a5] hover:text-[#ef5350] text-xs"
                                                >×</button>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {alerts.some((a) => a.triggered) && (
                            <button
                                onClick={handleClear}
                                className="mt-3 w-full text-[10px] text-[#00B7FF]/60 hover:text-[#00D9FF]"
                            >
                                Clear fired alerts
                            </button>
                        )}
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}