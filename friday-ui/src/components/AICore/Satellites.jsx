import React from "react";

export default function Satellites({ state = 'idle' }){
  const base = [
    { r: '100px', size: 6, dur: 7, dir: 'cw' },
    { r: '140px', size: 8, dur: 11, dir: 'ccw' },
    { r: '90px', size: 5, dur: 9, dir: 'cw' },
    { r: '120px', size: 7, dur: 13, dir: 'ccw' },
    { r: '150px', size: 6, dur: 18, dir: 'cw' },
    { r: '110px', size: 5, dur: 22, dir: 'ccw' },
    { r: '130px', size: 7, dur: 16, dir: 'cw' },
  ];

  const speedMap = { idle: 1, listening: 0.75, thinking: 0.6, speaking: 0.45, verified: 1.15, alert: 0.5 };
  const sizeMap = { idle: 1, listening: 1.05, thinking: 1.1, speaking: 1.18, verified: 1.25, alert: 0.85 };
  const glowMap = { idle: 0.45, listening: 0.75, thinking: 0.9, speaking: 1, verified: 0.7, alert: 0.55 };
  const m = speedMap[state] ?? 1;
  const sizeFactor = sizeMap[state] ?? 1;
  const glowIntensity = glowMap[state] ?? 0.5;

  return (
    <>
      {base.map((s, i) => {
        const size = s.size * sizeFactor;
        const opacity = 0.35 + glowIntensity * (0.15 + i * 0.06);
        const blur = 4 + i * 1.5;

        return (
          <div
            key={i}
            className="satellite"
            style={{
              width: `${size}px`,
              height: `${size}px`,
              left: '50%',
              top: '50%',
              transform: 'translate(-50%,-50%)',
              ['--radius']: s.r,
              animation: `${s.dir === 'cw' ? 'satCW' : 'satCCW'} ${s.dur * m}s linear infinite`,
              opacity,
              boxShadow: `0 0 ${blur}px rgba(0,230,255,${opacity})`,
            }}
          />
        );
      })}
    </>
  )
}
