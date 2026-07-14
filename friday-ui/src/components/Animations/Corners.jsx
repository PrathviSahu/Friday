/* Four corner HUD brackets */
export default function Corners() {
    const size = 18;
    const corners = [
        { top: 16, left: 16,  borderTop: true,  borderLeft: true  },
        { top: 16, right: 16, borderTop: true,  borderRight: true },
        { bottom: 16, left: 16,  borderBottom: true, borderLeft: true  },
        { bottom: 16, right: 16, borderBottom: true, borderRight: true },
    ];

    return (
        <>
            {corners.map((pos, i) => (
                <div
                    key={i}
                    className="absolute pointer-events-none"
                    style={{
                        ...pos,
                        width: size, height: size,
                        borderTop:    pos.borderTop    ? '1px solid rgba(0,183,255,0.4)' : 'none',
                        borderBottom: pos.borderBottom ? '1px solid rgba(0,183,255,0.4)' : 'none',
                        borderLeft:   pos.borderLeft   ? '1px solid rgba(0,183,255,0.4)' : 'none',
                        borderRight:  pos.borderRight  ? '1px solid rgba(0,183,255,0.4)' : 'none',
                    }}
                />
            ))}
            {/* Side tick marks */}
            <div className="absolute left-6 top-1/2 -translate-y-1/2 flex flex-col gap-2 pointer-events-none">
                {[...Array(5)].map((_, i) => (
                    <div key={i} className="w-1 h-px bg-[#00B7FF]/25" />
                ))}
            </div>
            <div className="absolute right-6 top-1/2 -translate-y-1/2 flex flex-col gap-2 pointer-events-none">
                {[...Array(5)].map((_, i) => (
                    <div key={i} className="w-1 h-px bg-[#00B7FF]/25" />
                ))}
            </div>
        </>
    );
}
