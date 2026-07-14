import { useState, useEffect } from 'react';

export default function Clock() {
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

    return (
        <div className="flex items-center gap-3 font-orbitron text-right">
            <div>
                <div className="text-2xl font-bold text-[#DFFAFF] tracking-widest leading-none drop-shadow-[0_0_8px_rgba(0,183,255,0.5)]">
                    {h}:{m} <span className="text-sm text-[#00B7FF]">{ampm}</span>
                </div>
                <div className="text-[9px] text-[#00B7FF]/60 tracking-[0.2em] mt-0.5">{dateStr}</div>
            </div>
            <svg width="52" height="52">
                <circle cx={cx} cy={cy} r={R} fill="none" stroke="rgba(0,183,255,0.15)" strokeWidth="1.5" />
                <circle
                    cx={cx} cy={cy} r={R} fill="none"
                    stroke="#00B7FF" strokeWidth="1.5"
                    strokeDasharray={`${dash} ${arc}`}
                    strokeLinecap="round"
                    transform={`rotate(-90 ${cx} ${cy})`}
                    style={{ filter: 'drop-shadow(0 0 4px #00B7FF)' }}
                />
                <text x={cx} y={cy + 4} textAnchor="middle" fill="#00B7FF" fontSize="8" fontFamily="Orbitron">
                    {String(s).padStart(2, '0')}
                </text>
            </svg>
        </div>
    );
}
