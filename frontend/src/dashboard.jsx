import React, { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";
import { createChart, CrosshairMode } from "lightweight-charts";

const SOCKET_URL = "http://localhost:5000";

export default function Dashboard() {
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const candleSeriesRef = useRef();
  const [socket, setSocket] = useState(null);
  const [candleCount, setCandleCount] = useState(0);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    // Initialize Chart
    chartRef.current = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: { backgroundColor: "#ffffff", textColor: "#000" },
      grid: { vertLines: { color: "#eee" }, horzLines: { color: "#eee" } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#ccc" },
      timeScale: { borderColor: "#ccc", timeVisible: true },
    });

    candleSeriesRef.current = chartRef.current.addCandlestickSeries({
      upColor: "#4caf50", downColor: "#f44336", borderVisible: false,
      wickUpColor: "#4caf50", wickDownColor: "#f44336",
    });

    // Connect Socket
    const sock = io(SOCKET_URL);
    setSocket(sock);

    // Historical Candles
    sock.on("candles", (candles) => {
      if (Array.isArray(candles) && candles.length > 0) {
        console.log(`Received ${candles.length} historical candles:`, candles.slice(0, 3));
        candleSeriesRef.current.setData(candles);
        setCandleCount(candles.length);
        
        // Log timestamp information for debugging
        const firstTime = new Date(candles[0].time * 1000);
        const lastTime = new Date(candles[candles.length-1].time * 1000);
        console.log(`Time range: ${firstTime.toISOString()} to ${lastTime.toISOString()}`);
      }
    });

    // Live Updates
    sock.on("candle_update", (latestCandle) => {
      if (latestCandle) {
        console.log("Live update:", latestCandle);
        candleSeriesRef.current.update(latestCandle);
        setLastUpdate(new Date().toLocaleTimeString());
      }
    });

    // Trading Signals
    sock.on("trading_signal", (signal) => {
      console.log("Trading signal:", signal);
    });

    sock.on("trade_executed", (trade) => {
      console.log("Trade executed:", trade);
    });

    // Handle resize
    const handleResize = () => {
      chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      sock.disconnect();
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <div style={{ padding: '20px' }}>
      <h2>Trading Dashboard</h2>
      <div style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#f0f0f0' }}>
        <strong>Status:</strong> Connected | <strong>Candles:</strong> {candleCount} | 
        <strong> Last Update:</strong> {lastUpdate || 'None'}
      </div>
      <div ref={chartContainerRef} style={{ width: "100%", height: "500px" }}></div>
    </div>
  );
}