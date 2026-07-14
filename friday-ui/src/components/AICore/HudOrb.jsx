import React from "react";
import "./Orb.css";
import AICore from "./AICore";

export default function HudOrb({ size = 340 }) {
  return (
    <div className="orb-container" style={{ width: size, height: size }}>
      <AICore />
    </div>
  );
}
