import { useState, useEffect } from 'react';

export default function Clock({ large = false }) {
    const [now, setNow] = useState(new Date());
    useEffect(() => {
        const id = setInterval(() => setNow(new Date()), 1000);
        return () => clearInterval(id);
    }, []);

    const h   = now.getHours() % 12 || 12;
    const m   = String(now.getMinutes()).padStart(2, '0');
    const s   = now.getSeconds();
    const ampm = now.getHours() >= 12 ? 'PM' : 'AM';

    const dateStr = now.toLocaleDateString('en-US', {
        weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
    }).toUpperCase();

    // Arc progress for seconds
    const pct = s / 60;
    const R   = 22, cx = 26, cy = 26;
    const arc = 2 * Math.PI * R;
    const dash = pct * arc;

    if (large) {
        return (
            <div className="flex flex-col items-center gap-2 font-sans">
                <div className="text-[4rem] font-bold text-slate-100 tracking-[0.15em] leading-none">
                    {h}:{m}
                    <span className="text-2xl text-slate-400 ml-3">{ampm}</span>
                </div>
                <div className="text-[11px] text-slate-400/60 tracking-[0.35em] uppercase">{dateStr}</div>
                <div className="mt-1 flex items-center gap-2">
                    <svg width="36" height="36">
                        <circle cx={18} cy={18} r={14} fill="none" stroke="rgba(148,163,184,0.15)" strokeWidth="1.5" />
                        <circle
                            cx={18} cy={18} r={14} fill="none"
                            stroke="#60a5fa" strokeWidth="1.5"
                            strokeDasharray={`${pct * 2 * Math.PI * 14} ${2 * Math.PI * 14}`}
                            strokeLinecap="round"
                            transform="rotate(-90 18 18)"
                        />
                        <text x={18} y={22} textAnchor="middle" fill="#94a3b8" fontSize="7" fontFamily="Inter">
                            {String(s).padStart(2, '0')}
                        </text>
                    </svg>
                </div>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-3 font-sans text-right">
            <div>
                <div className="text-2xl font-bold text-slate-200 tracking-widest leading-none">
                    {h}:{m} <span className="text-sm text-slate-400">{ampm}</span>
                </div>
                <div className="text-[9px] text-slate-400/50 tracking-[0.15em] mt-0.5">{dateStr}</div>
            </div>
            <svg width="52" height="52">
                <circle cx={cx} cy={cy} r={R} fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth="1.5" />
                <circle
                    cx={cx} cy={cy} r={R} fill="none"
                    stroke="#60a5fa" strokeWidth="1.5"
                    strokeDasharray={`${dash} ${arc}`}
                    strokeLinecap="round"
                    transform={`rotate(-90 ${cx} ${cy})`}
                />
                <text x={cx} y={cy + 4} textAnchor="middle" fill="#94a3b8" fontSize="8" fontFamily="Inter">
                    {String(s).padStart(2, '0')}
                </text>
            </svg>
        </div>
    );
}
