import { useState, useRef, useEffect, useCallback } from 'react';

// SVG overlay for geometric drawing on top of the lightweight-charts canvas.
// Uses the chart's coordinate mappers (time<->x, price<->y) so drawings stay
// glued to the data when the user pans/zooms. Drawings persist per symbol.
//
// Props:
//   chart        - lightweight-charts IChartApi instance
//   series       - the candlestick series (ISeriesApi) for price<->y mapping
//   symbol       - used as the localStorage key
//   drawMode     - 'trend' | 'hline' | 'ray' | 'rect' | null
//   clearSignal  - increment to wipe all drawings for this symbol

const KEY = (sym) => `friday_drawings_${sym}`;

function load(sym) {
    try {
        const raw = localStorage.getItem(KEY(sym));
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function save(sym, list) {
    try {
        localStorage.setItem(KEY(sym), JSON.stringify(list));
    } catch {
        /* ignore */
    }
}

export default function DrawOverlay({ chart, series, symbol, drawMode, clearSignal }) {
    const [drawings, setDrawings] = useState(() => load(symbol));
    const [draft, setDraft] = useState(null); // in-progress drawing
    const drawingRef = useRef(false);
    const svgRef = useRef(null);

    useEffect(() => {
        setDrawings(load(symbol));
        setDraft(null);
    }, [symbol]);

    useEffect(() => {
        save(symbol, drawings);
    }, [symbol, drawings]);

    useEffect(() => {
        if (clearSignal) {
            setDrawings([]);
            setDraft(null);
        }
    }, [clearSignal]);

    const toPoint = useCallback(
        (e) => {
            const rect = svgRef.current.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const time = chart.timeScale().coordinateToTime(x);
            const price = series.coordinateToPrice(y);
            return { x, y, time, price };
        },
        [chart, series],
    );

    const onDown = (e) => {
        if (!drawMode || !chart || !series) return;
        drawingRef.current = true;
        const p = toPoint(e);
        const start = drawMode === 'hline' ? { time: p.time, price: p.price, x: p.x, y: p.y } : { time: p.time, price: p.price };
        setDraft({ type: drawMode, p1: start, p2: start });
    };

    const onMove = (e) => {
        if (!drawingRef.current || !draft) return;
        const p = toPoint(e);
        setDraft((d) => (d ? { ...d, p2: { time: p.time, price: p.price } } : d));
    };

    const onUp = () => {
        if (!drawingRef.current || !draft) return;
        drawingRef.current = false;
        const d = draft;
        setDraft(null);
        // Require a minimum drag (unless horizontal line).
        if (d.type !== 'hline') {
            const t1 = d.p1.time,
                t2 = d.p2.time,
                pr1 = d.p1.price,
                pr2 = d.p2.price;
            if (t1 == null || t2 == null || (Math.abs(t1 - t2) < 1 && Math.abs(pr1 - pr2) < 1e-6)) return;
        }
        if (d.type === 'hline' && d.p1.price == null) return;
        setDrawings((prev) => [...prev, { ...d, id: `draw_${Date.now()}_${Math.floor(Math.random() * 1e6)}` }]);
    };

    const remove = (id) => setDrawings((prev) => prev.filter((d) => d.id !== id));

    // Map a (time, price) pair to pixel coords; null if off-chart.
    const xy = (time, price) => {
        const x = chart.timeScale().timeToCoordinate(time);
        const y = series.priceToCoordinate(price);
        if (x == null || y == null) return null;
        return { x, y };
    };

    const renderShape = (d, isDraft) => {
        const a = xy(d.p1.time, d.p1.price);
        const b = xy(d.p2.time, d.p2.price);
        const stroke = isDraft ? '#00D9FF' : '#FFB454';
        if (d.type === 'hline') {
            if (a == null) return null;
            return (
                <line key={d.id || 'draft'} x1={0} y1={a.y} x2="100%" y2={a.y} stroke={stroke} strokeWidth={1.5} strokeDasharray="6 4" />
            );
        }
        if (a == null || b == null) return null;
        if (d.type === 'trend' || d.type === 'ray') {
            const ext = d.type === 'ray' ? 2.5 : 1;
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            return (
                <line
                    key={d.id || 'draft'}
                    x1={a.x}
                    y1={a.y}
                    x2={a.x + dx * ext}
                    y2={a.y + dy * ext}
                    stroke={stroke}
                    strokeWidth={1.5}
                />
            );
        }
        // rectangle
        return (
            <rect
                key={d.id || 'draft'}
                x={Math.min(a.x, b.x)}
                y={Math.min(a.y, b.y)}
                width={Math.abs(b.x - a.x)}
                height={Math.abs(b.y - a.y)}
                fill="rgba(255,180,84,0.08)"
                stroke={stroke}
                strokeWidth={1.5}
            />
        );
    };

    const allShapes = [
        ...drawings,
        ...(draft ? [{ ...draft, id: 'draft' }] : []),
    ];

    return (
        <svg
            ref={svgRef}
            className="absolute inset-0 w-full h-full"
            style={{ pointerEvents: drawMode ? 'auto' : 'none', cursor: drawMode ? 'crosshair' : 'default' }}
            onMouseDown={onDown}
            onMouseMove={onMove}
            onMouseUp={onUp}
            onMouseLeave={onUp}
        >
            {allShapes.map((d) => (
                <g key={d.id}>
                    {renderShape(d, d.id === 'draft')}
                    {d.id !== 'draft' && (
                        <DeleteHandle
                            pos={xy(d.p1.time, d.p1.price)}
                            onClick={() => remove(d.id)}
                        />
                    )}
                </g>
            ))}
        </svg>
    );
}

function DeleteHandle({ pos, onClick }) {
    if (!pos) return null;
    return (
        <g
            transform={`translate(${pos.x + 6}, ${pos.y - 6})`}
            style={{ pointerEvents: 'auto', cursor: 'pointer' }}
            onMouseDown={(e) => {
                e.stopPropagation();
                onClick();
            }}
        >
            <circle r={7} fill="#ef5350" />
            <text x={0} y={3} textAnchor="middle" fontSize="9" fill="#fff" fontFamily="monospace">
                ×
            </text>
        </g>
    );
}
