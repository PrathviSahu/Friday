import { formatSymbol } from '../../services/market';

// Scrolling marquee of watchlist quotes across the top of the trading view.
export default function TickerTape({ symbols, quotes }) {
    const items = symbols.map((sym) => {
        const q = quotes[sym];
        const chg = q?.changePercent;
        const up = chg != null && chg >= 0;
        return {
            sym,
            label: formatSymbol(sym),
            price: q?.price,
            chg,
            up,
        };
    });

    if (!items.length) return null;
    // Duplicate the list so the CSS marquee loops seamlessly.
    const loop = [...items, ...items];

    return (
        <div className="relative h-8 overflow-hidden border-b border-[#1e222d] bg-[#0b0e17]">
            <div
                className="absolute whitespace-nowrap flex items-center h-full will-change-transform"
                style={{ animation: 'friday-tape 38s linear infinite' }}
            >
                {loop.map((it, i) => (
                    <span key={i} className="inline-flex items-center gap-2 px-5 text-[11px] font-grotesk">
                        <span className="text-[#DFFAFF] tracking-wide">{it.label}</span>
                        <span className="text-[#8b93a5]">
                            {it.price != null ? it.price.toLocaleString() : '—'}
                        </span>
                        <span className={it.up ? 'text-[#26a69a]' : 'text-[#ef5350]'}>
                            {it.chg == null ? '' : `${it.up ? '+' : ''}${it.chg.toFixed(2)}%`}
                        </span>
                        <span className="text-[#1e222d]">|</span>
                    </span>
                ))}
            </div>
            <style>{`
                @keyframes friday-tape {
                    0% { transform: translateX(0); }
                    100% { transform: translateX(-50%); }
                }
            `}</style>
        </div>
    );
}
