// src/IndicatorSelector.tsx
import React from "react";

export default function IndicatorSelector() {
  return (
    <div style={{ padding: 15, background: "#374151", borderRadius: 8, marginTop: 15 }}>
      <h4 style={{ color: "#f9fafb", marginBottom: 10 }}>📊 Indicators</h4>
      <div style={{ display: "flex", gap: 10 }}>
        <button style={{ padding: "8px 16px", background: "#10b981", color: "white", border: "none", borderRadius: 5 }}>Add RSI</button>
        <button style={{ padding: "8px 16px", background: "#3b82f6", color: "white", border: "none", borderRadius: 5 }}>Add EMA</button>
      </div>
    </div>
  );
}