import React from 'react';

export default function ScanLines() {
    return (
        <div className="absolute inset-0 pointer-events-none z-3 overflow-hidden">
            <div className="w-full h-[2px] bg-gradient-to-r from-transparent via-cyan-500/10 to-transparent absolute top-0 left-0 animate-[scanlineMove_8s_infinite_linear]" />
        </div>
    );
}
