import React, { useEffect, useRef, useState } from "react";
import io from "socket.io-client";
import ChartComponent from "./ChartComponent";

export default function TradingDashboard() {
  const socketRef = useRef<any>(null);
  const [candles, setCandles] = useState<any[]>([]);
  const [price, setPrice] = useState(880.30421);
  const [trades, setTrades] = useState<any[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [realMode, setRealMode] = useState(false);
  const [showVol, setShowVol] = useState(true);
  const [showSMA, setShowSMA] = useState(true);
  const [showRSI, setShowRSI] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [debug, setDebug] = useState(false);

  const log = (msg: string) => setLogs(p => [...p.slice(-99), `[${new Date().toLocaleTimeString()}] ${msg}`]);

  useEffect(() => {
    log("QUANTUMTRADER PRO v7.1 ONLINE");

    const socket = io("", {
      transports: ["polling", "websocket"],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
      forceNew: false
    });

    socketRef.current = socket;

    socket.on("connect", () => {
      log("DASHBOARD CONNECTED TO FLASK");
    });

    socket.on("connect_error", (err: any) => {
      log(`CONNECTION FAILED: ${err.message}`);
    });

    socket.on("reconnect", (attempt: number) => {
      log(`RECONNECTED (attempt ${attempt})`);
    });

    socket.on("price_update", (data: any) => {
      setPrice(data.price);
    });

    socket.on("candles_update", (data: any) => {
      setCandles(data.candles || []);
      log(`CANDLES: ${data.count}`);
    });

    socket.on("trade_placed", (trade: any) => {
      setTrades(p => [...p, trade]);
      log(`TRADE: ${trade.type} @ $${trade.amount}`);
    });

    socket.on("system_status", (data: any) => {
      setRealMode(data.mode === "REAL");
      log(`MODE: ${data.mode}`);
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  const emergencyClose = () => {
    socketRef.current?.emit("emergency_close_all");
    log("EMERGENCY CLOSE ALL");
  };

  return (
    <div style={{ padding: 24, background: "#0a0a0a", color: "#fff", minHeight: "100vh", fontFamily: "'Courier New', monospace" }}>
      {realMode && (
        <div style={{ position: "fixed", top: 16, right: 16, zIndex: 9999, background: "#ff1744", padding: "16px 32px", borderRadius: 16, boxShadow: "0 0 30px #ff1744", fontWeight: "bold" }}>
          LIVE FIRE ENABLED
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "3.5rem", background: "linear-gradient(90deg, #00d4ff, #7c3aed)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            QUANTUMTRADER PRO
          </h1>
          <p style={{ margin: "8px 0", fontSize: "1.4rem", color: "#00d4ff" }}>
            R_100 • ${price.toFixed(5)} • {new Date().toLocaleTimeString()}
          </p>
        </div>
        <div style={{ display: "flex", gap: 16 }}>
          <button onClick={emergencyClose} style={{ padding: "14px 28px", background: "#ff1744", border: "none", borderRadius: 30, color: "white", fontWeight: "bold", cursor: "pointer", boxShadow: "0 0 20px #ff1744" }}>
            KILL SWITCH
          </button>
          <button onClick={() => setDebug(!debug)} style={{ padding: "14px 28px", background: debug ? "#ff9100" : "#1a1a1a", border: "2px solid #ff9100", borderRadius: 30, color: "white", cursor: "pointer" }}>
            DEBUG
          </button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
        {["Volume", "SMA", "RSI"].map(ind => (
          <button
            key={ind}
            onClick={() => {
              if (ind === "Volume") setShowVol(!showVol);
              if (ind === "SMA") setShowSMA(!showSMA);
              if (ind === "RSI") setShowRSI(!showRSI);
            }}
            style={{
              padding: "12px 24px", borderRadius: 30,
              background: (ind === "Volume" ? showVol : ind === "SMA" ? showSMA : showRSI) ? "#00d4ff" : "#333",
              color: "white", border: "none", fontWeight: "bold", cursor: "pointer"
            }}
          >
            {ind}
          </button>
        ))}
      </div>

      <div style={{ background: "#1a1a1a", borderRadius: 20, overflow: "hidden", marginBottom: 32, boxShadow: "0 0 30px rgba(0,212,255,0.3)" }}>
        <ChartComponent candleData={candles} showVolume={showVol} showSMA={showSMA} showRSI={showRSI} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <div style={{ background: "#16213e", padding: 24, borderRadius: 20 }}>
          <h2 style={{ color: "#00d4ff", margin: "0 0 16px" }}>Signals ({signals.length})</h2>
          {signals.slice().reverse().map((s, i) => (
            <div key={i} style={{
              padding: 16, margin: "8px 0", borderRadius: 12,
              background: s.signal === "buy" ? "rgba(0,200,83,0.2)" : "rgba(255,23,68,0.2)"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{s.strategy}</strong>
                <span style={{ color: s.signal === "buy" ? "#00c853" : "#ff1744" }}>{s.signal.toUpperCase()}</span>
              </div>
              <div style={{ fontSize: "0.9rem" }}>@ ${s.price?.toFixed(5)}</div>
            </div>
          ))}
        </div>
        <div style={{ background: "#16213e", padding: 24, borderRadius: 20 }}>
          <h2 style={{ color: "#00d4ff", margin: "0 0 16px" }}>Trades ({trades.length})</h2>
          {trades.map(t => (
            <div key={t.id} style={{
              padding: 16, margin: "8px 0", borderRadius: 12,
              background: t.type === "CALL" ? "rgba(0,200,83,0.15)" : "rgba(255,23,68,0.15)",
              borderLeft: t.is_real ? "6px solid #ff1744" : "none"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div>
                  <strong>{t.type}</strong> • {t.strategy || "AI"}
                  {t.is_real && <span style={{ marginLeft: 8, background: "#ff1744", padding: "4px 10px", borderRadius: 8, fontSize: "0.7rem" }}>REAL</span>}
                </div>
                <span style={{ color: "#0f0" }}>+${t.profit || 0.8}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {debug && (
        <div style={{ marginTop: 32, background: "#000", padding: 24, borderRadius: 20, maxHeight: 400, overflow: "auto", border: "1px solid #0f0", fontFamily: "monospace" }}>
          <h2 style={{ color: "#ff9100" }}>QUANTUM DEBUG v7.1</h2>
          {logs.map((l, i) => <div key={i} style={{ color: "#0f0", fontSize: "0.85rem" }}>{l}</div>)}
        </div>
      )}
    </div>
  );
}