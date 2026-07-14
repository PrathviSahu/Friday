import React from "react";

export default function Rings({ state = 'idle' }) {
  const multiplierMap = {
    idle: 1,
    listening: 0.55,
    thinking: 0.4,
    speaking: 0.35,
    verified: 1.15,
    alert: 0.45,
  };
  const m = multiplierMap[state] ?? 1;
  const strokeMap = {
    idle: '#4eeeff',
    listening: '#82f5ff',
    thinking: '#f0c362',
    speaking: '#feffff',
    verified: '#a5ffe0',
    alert: '#ff8a70',
  };

  return (
    <div className="hud-rings" aria-hidden>
      <svg viewBox="0 0 420 420">
        <circle className="ring ring1" cx="210" cy="210" r="80" style={{ animationDuration: `${9 * m}s`, stroke: strokeMap[state] }} />
        <circle className="ring ring2" cx="210" cy="210" r="110" style={{ animationDuration: `${16 * m}s`, stroke: strokeMap[state] }} />
        <circle className="ring ring3" cx="210" cy="210" r="140" style={{ animationDuration: `${25 * m}s`, stroke: strokeMap[state] }} />
        <circle className="ring ring4" cx="210" cy="210" r="170" style={{ animationDuration: `${35 * m}s`, stroke: strokeMap[state] }} />
        <circle className="ring ring5" cx="210" cy="210" r="200" style={{ animationDuration: `${45 * m}s`, stroke: strokeMap[state] }} />
      </svg>
    </div>
  );
}
