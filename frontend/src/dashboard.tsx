import React, { useEffect, useRef, useState } from "react";
import io, { Socket } from "socket.io-client";
import ChartComponent from "./ChartComponent";

interface Trade {
  id: string;
  type: "CALL" | "PUT";
  amount: number;
  strategy: string;
  confidence?: number;
  is_real: boolean;
  profit?: number;
  success?: boolean;
  exit_reason?: string;
  timestamp?: number;
}

interface SystemStatus {
  status: string;
  balance: number;
  mode: "DEMO" | "REAL";
  price: number;
  enabled_strategies: string[];
  mt5_bridge: boolean;
  halted: boolean;
  message?: string;
}

export default function TradingDashboard() {
  const socketRef = useRef<Socket | null>(null);

  const [candles, setCandles] = useState<any[]>([]);
  const [price, setPrice] = useState<number | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [system, setSystem] = useState<SystemStatus>({
    status: "connecting",
    balance: 10000,
    mode: "DEMO",
    price: 0,
    enabled_strategies: [],
    mt5_bridge: false,
    halted: false,
  });

  const [logs, setLogs] = useState<string[]>([]);
  const [debug, setDebug] = useState(false);
  const [show, setShow] = useState({
    vol: true,
    sma: true,
    rsi: true,
  });

  const log = (msg: string) => {
    const ts = new Date().toLocaleTimeString("en-US", { hour12: false });
    setLogs(prev => [...prev.slice(-200), `[${ts}] ${msg}`]);
  };

  const formatPrice = (p: number | null) => (p !== null ? p.toFixed(5) : "—.———");
  const formatBalance = (b: number | null) => (b !== null ? b.toFixed(2) : "—.——");
  const balanceColor = balance !== null
    ? balance > 10000 ? "#00ff9d" : balance < 9000 ? "#ff1744" : "#fff"
    : "#888";

  useEffect(() => {
    log("QUANTUMTRADER PRO v8.0 • DASHBOARD INITIALIZED");

    const socket = io("http://localhost:5000", {
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 20000,
    });

    socketRef.current = socket;

    socket.on("connect", () => log("SOCKET.IO CONNECTED"));
    socket.on("connect_error", (err) => log(`CONNECTION ERROR: ${err.message}`));
    socket.on("disconnect", () => log("SOCKET.IO DISCONNECTED"));

    socket.on("price_update", (data: { price: number }) => {
      if (typeof data.price === "number") setPrice(data.price);
    });

    socket.on("balance_update", (data: { balance: number }) => {
      if (typeof data.balance === "number") setBalance(data.balance);
    });

    socket.on("candles_update", (data: { candles: any[]; count: number }) => {
      setCandles(data.candles || []);
      log(`CANDLES UPDATED • ${data.count} bars`);
    });

    socket.on("trade_placed", (trade: Trade) => {
      if (!trade || !trade.id) return;
      setTrades(prev => [trade, ...prev].slice(0, 50));
      const type = trade.type === "CALL" ? "BUY" : "SELL";
      const real = trade.is_real ? " • LIVE FIRE" : "";
      log(`TRADE PLACED → ${type} $${trade.amount ?? 0} • ${trade.strategy}${real}`);
    });

    // BULLETPROOF trade_result — NO MORE CRASHES EVER
    socket.on("trade_result", (result: any) => {
      try {
        if (!result || typeof result !== "object" || !result.id) {
          return; // ignore test/demo garbage
        }

        setTrades(prev =>
          prev.map(t =>
            t.id === result.id
              ? {
                  ...t,
                  profit: typeof result.profit === "number" ? result.profit : null,
                  success: typeof result.success === "boolean" ? result.success : null,
                  exit_reason: typeof result.exit_reason === "string" ? result.exit_reason : "closed",
                }
              : t
          )
        );

        // Only log real P&L
        if (typeof result.profit === "number") {
          const emoji = result.success ? "PROFIT" : "LOSS";
          log(`${emoji} TRADE CLOSED • P&L: $${result.profit.toFixed(2)} • ${result.exit_reason || "closed"}`);
        }
      } catch (e) {
        console.warn("Ignored malformed trade_result");
      }
    });

    socket.on("system_status", (data: SystemStatus) => {
      setSystem(data);
      if (typeof data.balance === "number") setBalance(data.balance);
      const mode = data.mode === "REAL" ? "LIVE TRADING" : "DEMO MODE";
      const mt5 = data.mt5_bridge ? "MT5 BRIDGE ACTIVE" : "MT5 OFFLINE";
      log(`SYSTEM → ${mode} • Balance: $${data.balance.toFixed(2)} • ${mt5}`);
      if (data.halted) log("TRADING HALTED • DAILY LOSS LIMIT");
    });

    socket.on("system_alert", (alert: any) => {
      log(`ALERT [${alert.type?.toUpperCase() || "?"}] ${alert.title || ""}: ${alert.message || ""}`);
    });

    socket.on("mt5_signal_sent", () => {
      log("MT5 SIGNAL → SENT TO GITHUB (check signals.json)");
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, []);

  const sendTestSignal = () => {
    socketRef.current?.emit("test_mt5_signal");
    log("TEST MT5 SIGNAL SENT — CHECK GITHUB signals.json");
  };

  const manualTrade = (direction: "buy" | "sell") => {
    socketRef.current?.emit("manual_trade", { signal: direction });
    log(`MANUAL ${direction.toUpperCase()} SIGNAL SENT`);
  };

  const emergencyClose = () => {
    socketRef.current?.emit("emergency_close_all");
    log("EMERGENCY CLOSE ALL CONTRACTS FIRED");
  };

  return (
    <>
      <style>{`
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 20px #ff1744; }
          50% { box-shadow: 0 0 60px #ff1744; }
        }
        body { margin: 0; background: #0d001a; font-family: 'Space Grotesk', sans-serif; }
      `}</style>

      <div style={{ padding: 24, background: "#0d001a", color: "#e0e0ff", minHeight: "100vh" }}>
        {system.mode === "REAL" && (
          <div style={{
            position: "fixed", top: 16, left: "50%", transform: "translateX(-50%)", zIndex: 9999,
            background: "linear-gradient(90deg, #ff1744, #c62828)", padding: "16px 48px",
            borderRadius: 50, boxShadow: "0 0 60px #ff1744", fontWeight: "bold",
            fontSize: "1.5rem", letterSpacing: 3, animation: "pulse 2s infinite",
          }}>
            LIVE TRADING ACTIVE • REAL MONEY AT RISK
          </div>
        )}

        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <h1 style={{
            margin: 0, fontSize: "4.5rem", fontWeight: 900,
            background: "linear-gradient(90deg, #00ffff, #7c3aed, #ff1744)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>
            QUANTUMTRADER PRO v8.0
          </h1>
          <div style={{ fontSize: "1.6rem", marginTop: 12, color: "#00ffff" }}>
            Volatility 100 Index •{" "}
            <span style={{ fontWeight: "bold", color: "#fff" }}>${formatPrice(price)}</span>
            {" • "}Balance:{" "}
            <span style={{ color: balanceColor }}>${formatBalance(balance)}</span>
            {" • "}{new Date().toLocaleTimeString()}
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "center", gap: 16, flexWrap: "wrap", marginBottom: 32 }}>
          <button onClick={() => manualTrade("buy")} style={{
            padding: "16px 40px", background: "#00c853", border: "none", borderRadius: 50,
            color: "white", fontWeight: "bold", fontSize: "1.3rem", cursor: "pointer",
            boxShadow: "0 0 30px #00c85388",
          }}>MANUAL BUY</button>

          <button onClick={() => manualTrade("sell")} style={{
            padding: "16px 40px", background: "#ff1744", border: "none", borderRadius: 50,
            color: "white", fontWeight: "bold", fontSize: "1.3rem", cursor: "pointer",
            boxShadow: "0 0 30px #ff174488",
          }}>MANUAL SELL</button>

          <button onClick={sendTestSignal} style={{
            padding: "16px 40px", background: "#ff9100", border: "none", borderRadius: 50,
            color: "black", fontWeight: "bold", fontSize: "1.3rem", cursor: "pointer",
          }}>TEST MT5</button>

          <button onClick={emergencyClose} style={{
            padding: "16px 40px", background: "#000", border: "4px solid #ff1744", borderRadius: 50,
            color: "#ff1744", fontWeight: "bold", fontSize: "1.3rem", cursor: "pointer",
          }}>KILL SWITCH</button>

          <button onClick={() => setDebug(d => !d)} style={{
            padding: "16px 40px", background: debug ? "#ff1744" : "#1a0033",
            border: "2px solid #ff9100", borderRadius: 50, color: "#ff9100",
            fontWeight: "bold", cursor: "pointer",
          }}>
            DEBUG {debug ? "ON" : "OFF"}
          </button>
        </div>

        <div style={{ textAlign: "center", marginBottom: 24 }}>
          {["Volume", "SMA", "RSI"].map(ind => (
            <button
              key={ind}
              onClick={() => {
                if (ind === "Volume") setShow(s => ({ ...s, vol: !s.vol }));
                if (ind === "SMA") setShow(s => ({ ...s, sma: !s.sma }));
                if (ind === "RSI") setShow(s => ({ ...s, rsi: !s.rsi }));
              }}
              style={{
                margin: "0 8px", padding: "10px 24px", borderRadius: 30,
                background: (ind === "Volume" ? show.vol : ind === "SMA" ? show.sma : show.rsi) ? "#7c3aed" : "#16213e",
                color: "white", border: "none", fontWeight: "bold", cursor: "pointer",
              }}
            >
              {ind} {ind === "Volume" ? (show.vol ? "ON" : "OFF") : ind === "SMA" ? (show.sma ? "ON" : "OFF") : (show.rsi ? "ON" : "OFF")}
            </button>
          ))}
        </div>

        <div style={{
          background: "#0f0a1f", borderRadius: 24, overflow: "hidden",
          marginBottom: 32, boxShadow: "0 0 50px rgba(124, 58, 237, 0.5)",
        }}>
          <ChartComponent
            candleData={candles}
            showVolume={show.vol}
            showSMA={show.sma}
            showRSI={show.rsi}
            currentPrice={price}
          />
        </div>

        {debug && (
          <div style={{
            marginTop: 32, background: "#000", padding: 24, borderRadius: 20,
            border: "2px solid #00ff00", boxShadow: "0 0 30px #00ff0088",
            maxHeight: 500, overflow: "auto",
          }}>
            <h2 style={{ color: "#00ff00", margin: "0 0 16px" }}>DEBUG CONSOLE</h2>
            {logs.map((l, i) => (
              <div key={i} style={{ color: "#00ff9d", fontSize: "0.9rem", fontFamily: "monospace" }}>
                {l}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}