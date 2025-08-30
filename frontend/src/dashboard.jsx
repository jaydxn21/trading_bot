// src/components/Dashboard.jsx
import React, { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";
import { createChart, CrosshairMode } from "lightweight-charts";

const SOCKET_URL = "http://localhost:5000";

export default function Dashboard() {
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const seriesRef = useRef();
  const smaRef = useRef();
  const lastTimeRef = useRef(null);
  const socketRef = useRef(null);

  // ────────────── State ──────────────
  const [candles, setCandles] = useState([]);
  const [balance, setBalance] = useState(0);
  const [openPnL, setOpenPnL] = useState(0);
  const [equity, setEquity] = useState(0);
  const [lastPrice, setLastPrice] = useState(null);
  const [openTrades, setOpenTrades] = useState([]);
  const [tradeConfidence, setTradeConfidence] = useState({ signal: "-", confidence: 0 });

  // ────────────── Helpers ──────────────
  const normalize = (r) => ({
    time: Number(r.time),
    open: Number(r.open),
    high: Number(r.high),
    low: Number(r.low),
    close: Number(r.close),
  });

  function computeSMA(data, period = 20) {
    if (!data || data.length < period) return [];
    const out = [];
    let sum = 0;
    for (let i = 0; i < data.length; i++) {
      sum += data[i].close;
      if (i >= period) sum -= data[i - period].close;
      if (i >= period - 1) {
        out.push({ time: data[i].time, value: +(sum / period).toFixed(5) });
      }
    }
    return out;
  }

  // ────────────── Chart Setup ──────────────
  useEffect(() => {
    chartRef.current = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 520,
      layout: { background: { color: "#f9fafb" }, textColor: "#111827" },
      grid: { vertLines: { color: "#e5e7eb" }, horzLines: { color: "#e5e7eb" } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderVisible: true },
      timeScale: { timeVisible: true, secondsVisible: false },
    });

    seriesRef.current = chartRef.current.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    smaRef.current = chartRef.current.addLineSeries({
      color: "#2563eb",
      lineWidth: 2,
      priceLineVisible: false,
    });

    const handleResize = () =>
      chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chartRef.current.remove();
    };
  }, []);

  // ────────────── Socket.IO ──────────────
  useEffect(() => {
    const socket = io(SOCKET_URL, { transports: ["websocket"] });
    socketRef.current = socket;

    socket.on("connect", () => console.log("🟢 Connected to backend"));

    socket.on("history", (rows) => {
      if (!rows?.length) return;
      const map = new Map();
      for (const r of rows) map.set(normalize(r).time, normalize(r));
      const arr = Array.from(map.values()).sort((a, b) => a.time - b.time);
      setCandles(arr);
      seriesRef.current.setData(arr);
      lastTimeRef.current = arr[arr.length - 1]?.time ?? null;
      smaRef.current.setData(computeSMA(arr, 20));
    });

    socket.on("candle", (c) => {
      if (!c) return;
      const bar = normalize(c);
      const lastTime = lastTimeRef.current;
      setCandles((prev) => {
        let next = [...prev];
        if (!lastTime || bar.time > lastTime) {
          seriesRef.current.update(bar);
          lastTimeRef.current = bar.time;
          next.push(bar);
        } else if (bar.time === lastTime) {
          seriesRef.current.update(bar);
          next[next.length - 1] = bar;
        }
        if (next.length > 1000) next.splice(0, next.length - 1000);
        smaRef.current.setData(computeSMA(next, 20));
        return next;
      });
    });

    socket.on("account", (snap) => {
      if (!snap) return;
      setBalance(snap.balance ?? 0);
      setOpenPnL(snap.open_pnl ?? 0);
      setEquity(snap.equity ?? 0);
      setLastPrice(snap.last_price ?? null);
      setOpenTrades(Array.isArray(snap.open_trades) ? snap.open_trades : []);
    });

    socket.on("trade_update", (msg) => {
      if (msg?.open_trades) setOpenTrades(msg.open_trades);
      if (typeof msg?.balance === "number") setBalance(msg.balance);
    });

    socket.on("trade_confidence", (data) => {
      if (!data) return;
      setTradeConfidence({
        signal: data.signal ?? "-",
        confidence: Math.min(Math.max(data.confidence ?? 0, 0), 100),
      });
    });

    return () => socket.disconnect();
  }, []);

  // ────────────── Render ──────────────
  return (
    <div style={{ display: "flex", gap: 16, padding: 16, fontFamily: "system-ui", background: "#f3f4f6", minHeight: "100vh" }}>
      <div style={{ flex: 1 }}>
        <div
          style={{ height: 520, borderRadius: 12, overflow: "hidden", boxShadow: "0 4px 8px rgba(0,0,0,0.05)" }}
          ref={chartContainerRef}
        />
      </div>

      <div style={{ width: 360, display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Account panel */}
        <div style={cardStyle}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>💰 Account</div>
          <div>Balance: ${balance.toFixed(2)}</div>
          <div>Open PnL: {openPnL >= 0 ? "📈 +" : "📉 -"}${Math.abs(openPnL).toFixed(2)}</div>
          <div>Equity: ${equity.toFixed(2)}</div>
          <div>Last Price: {lastPrice != null ? lastPrice.toFixed(5) : "-"}</div>
        </div>

        {/* Analytics panel */}
        <div style={cardStyle}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>📊 Analytics</div>
          <div>Bars Loaded: {candles.length}</div>
          <div>SMA(20) of last bar: {smaRef.current ? smaRef.current._data?.slice(-1)[0]?.value.toFixed(5) : "-"}</div>
        </div>

        {/* Open trades panel */}
        <div style={cardStyle}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>⚡ Open Trades</div>
          {openTrades.length === 0 ? (
            <div style={{ color: "#6b7280", textAlign: "center", padding: 8 }}>No open trades</div>
          ) : openTrades.map((t) => {
            const pnl = lastPrice == null ? 0 : (t.type === "BUY" ? (lastPrice - t.entry) * t.lot : (t.entry - lastPrice) * t.lot);
            return (
              <div key={t.id} style={{ display: "flex", justifyContent: "space-between", padding: 6, marginBottom: 4, borderRadius: 6, background: pnl >= 0 ? "#d1fae5" : "#fee2e2" }}>
                <div>{t.symbol}</div>
                <div>{t.type}</div>
                <div style={{ fontWeight: 600 }}>{pnl >= 0 ? `+$${pnl.toFixed(2)}` : `-$${Math.abs(pnl).toFixed(2)}`}</div>
              </div>
            );
          })}
        </div>

        {/* Trade Confidence panel */}
        <div style={cardStyle}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>🔮 Trade Confidence</div>
          <div style={{ color: "#6b7280", fontStyle: "italic", marginBottom: 8, textAlign: "center" }}>
            Signal: {tradeConfidence.signal} ({tradeConfidence.confidence}%)
          </div>
          <div style={{
            height: 16,
            width: "100%",
            background: "#e5e7eb",
            borderRadius: 8,
            overflow: "hidden",
            display: "flex",
            alignItems: "center"
          }}>
            <div style={{
              width: `${tradeConfidence.confidence}%`,
              background: tradeConfidence.signal === "BUY" ? "#10b981" :
                          tradeConfidence.signal === "SELL" ? "#ef4444" : "#2563eb",
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontWeight: 700
            }}>
              {tradeConfidence.signal === "-" ? "⚡" : tradeConfidence.signal}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const cardStyle = {
  padding: 12,
  background: "#fff",
  borderRadius: 12,
  boxShadow: "0 2px 6px rgba(0,0,0,0.05)",
  display: "flex",
  flexDirection: "column",
  gap: 6,
};
