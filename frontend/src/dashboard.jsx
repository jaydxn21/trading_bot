import React, { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";
import { createChart, CrosshairMode } from "lightweight-charts";

const SOCKET_URL = "http://localhost:5000";

export default function Dashboard() {
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const candleSeriesRef = useRef();
  const socketRef = useRef();
  const [isConnected, setIsConnected] = useState(false);
  const shouldAutoScrollRef = useRef(true);
  const lastScrollTimeRef = useRef(0);

  useEffect(() => {
    // Initialize chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: { 
        background: { color: "#f9fafb" }, 
        textColor: "#111827" 
      },
      grid: { 
        vertLines: { color: "#e5e7eb" }, 
        horzLines: { color: "#e5e7eb" } 
      },
      crosshair: { 
        mode: CrosshairMode.Normal 
      },
      timeScale: { 
        timeVisible: true, 
        secondsVisible: false,
        borderColor: '#d1d5db',
        barSpacing: 15,
      },
      rightPriceScale: {
        borderColor: '#d1d5db',
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    // Track user scrolling
    const handleScroll = () => {
      const now = Date.now();
      lastScrollTimeRef.current = now;
      
      // If user scrolled recently, don't auto-scroll
      shouldAutoScrollRef.current = false;
      
      // Reset auto-scroll after 2 seconds of no scrolling
      setTimeout(() => {
        if (Date.now() - lastScrollTimeRef.current >= 2000) {
          const timeScale = chart.timeScale();
          const visibleRange = timeScale.getVisibleRange();
          const data = candleSeries.data;
          
          if (data && data.length > 0 && visibleRange) {
            const lastBarTime = data[data.length - 1].time;
            const isAtEnd = visibleRange.to >= lastBarTime - 60; // 60 seconds buffer
            shouldAutoScrollRef.current = isAtEnd;
          }
        }
      }, 2000);
    };

    // Subscribe to scroll events
    chart.timeScale().subscribeVisibleTimeRangeChange(handleScroll);

    // Initialize socket connection
    socketRef.current = io(SOCKET_URL);

    socketRef.current.on("connect", () => {
      console.log("Connected to server");
      setIsConnected(true);
    });

    socketRef.current.on("disconnect", () => {
      console.log("Disconnected from server");
      setIsConnected(false);
    });

    // Listen for initial candles data
    socketRef.current.on("candles", (candles) => {
      if (candles && candles.length > 0) {
        // Update chart with all candles
        candleSeries.setData(candles);
        
        // Auto-scroll to the end to show latest candle initially
        chart.timeScale().scrollToPosition(-5, false);
        shouldAutoScrollRef.current = true;
      }
    });

    // Listen for real-time candle updates
    socketRef.current.on("candle_update", (candle) => {
      if (candle) {
        // Update the chart with the latest candle
        candleSeries.update(candle);
        
        // Only auto-scroll if user hasn't manually scrolled away recently
        if (shouldAutoScrollRef.current) {
          chart.timeScale().scrollToPosition(-5, false);
        }
      }
    });

    // Handle window resize
    const handleResize = () => {
      if (chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.timeScale().unsubscribeVisibleTimeRangeChange(handleScroll);
      if (chartRef.current) {
        chartRef.current.remove();
      }
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  return (
    <div style={{ padding: '20px' }}>
      <h2>Trading Dashboard {isConnected ? "🟢" : "🔴"}</h2>
      <div 
        ref={chartContainerRef} 
        style={{ 
          width: "100%", 
          height: "500px",
          border: "1px solid #e5e7eb",
          borderRadius: "8px"
        }} 
      />
    </div>
  );
}