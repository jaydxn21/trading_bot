// Enhanced Dashboard.jsx with trade history display

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
  const [tradingStatus, setTradingStatus] = useState({});
  const [signals, setSignals] = useState([]);
  const [openPositions, setOpenPositions] = useState([]);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [performance, setPerformance] = useState({ 
    profit: 0, 
    trades: 0, 
    winRate: 0,
    wins: 0,
    losses: 0
  });
  const [activeTab, setActiveTab] = useState("signals");
  const shouldAutoScrollRef = useRef(true);
  const lastScrollTimeRef = useRef(0);

  useEffect(() => {
    // Initialize chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
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
      shouldAutoScrollRef.current = false;
      
      setTimeout(() => {
        if (Date.now() - lastScrollTimeRef.current >= 2000) {
          const timeScale = chart.timeScale();
          const visibleRange = timeScale.getVisibleRange();
          const data = candleSeries.data;
          
          if (data && data.length > 0 && visibleRange) {
            const lastBarTime = data[data.length - 1].time;
            const isAtEnd = visibleRange.to >= lastBarTime - 60;
            shouldAutoScrollRef.current = isAtEnd;
          }
        }
      }, 2000);
    };

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

    // Chart data handlers
    socketRef.current.on("candles", (candles) => {
      if (candles && candles.length > 0) {
        candleSeries.setData(candles);
        chart.timeScale().scrollToPosition(-5, false);
        shouldAutoScrollRef.current = true;
      }
    });

    socketRef.current.on("candle_update", (candle) => {
      if (candle) {
        candleSeries.update(candle);
        if (shouldAutoScrollRef.current) {
          chart.timeScale().scrollToPosition(-5, false);
        }
      }
    });

    // Trading event handlers
    socketRef.current.on("trading_signal", (signal) => {
      setSignals(prev => [...prev.slice(-9), signal]);
    });

    socketRef.current.on("trade_executed", (trade) => {
      setOpenPositions(prev => [...prev, trade]);
    });

    socketRef.current.on("trade_closed", (result) => {
      setOpenPositions(prev => prev.filter(p => p.id !== result.id));
      setTradeHistory(prev => [...prev, result]);
      
      const isWin = result.pnl > 0;
      setPerformance(prev => ({
        profit: prev.profit + result.pnl,
        trades: prev.trades + 1,
        wins: prev.wins + (isWin ? 1 : 0),
        losses: prev.losses + (isWin ? 0 : 1),
        winRate: prev.trades === 0 ? 0 : ((prev.wins + (isWin ? 1 : 0)) / (prev.trades + 1)) * 100
      }));
    });

    // Account updates
    socketRef.current.on("account_update", (summary) => {
      setTradingStatus(prev => ({ ...prev, ...summary }));
    });

    socketRef.current.on("trading_status", (status) => {
      setTradingStatus(status);
    });

    socketRef.current.on("demo_mode_changed", (data) => {
      setTradingStatus(prev => ({ ...prev, demo_mode: data.demo_mode }));
    });

    socketRef.current.on("risk_level_changed", (data) => {
      setTradingStatus(prev => ({ ...prev, risk_level: data.risk_level }));
    });

    socketRef.current.on("trade_history_update", (history) => {
      setTradeHistory(history);
    });

    socketRef.current.on("account_reset", (data) => {
      setTradingStatus(prev => ({ ...prev, balance: data.new_balance, equity: data.new_balance }));
      setOpenPositions([]);
      setTradeHistory([]);
      setPerformance({ profit: 0, trades: 0, winRate: 0, wins: 0, losses: 0 });
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
      if (chartRef.current) {
        chartRef.current.remove();
      }
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  // Calculate win rate from trade history
  const calculateWinRate = (history) => {
    if (history.length === 0) return 0;
    const wins = history.filter(trade => trade.pnl > 0).length;
    return (wins / history.length) * 100;
  };

  const toggleDemoMode = () => {
    socketRef.current.emit("toggle_demo_mode");
  };

  const setRiskLevel = (risk) => {
    socketRef.current.emit("set_risk_level", { risk });
  };

  const closeAllPositions = () => {
    socketRef.current.emit("close_all_positions");
  };

  const resetAccount = () => {
    if (window.confirm("Are you sure you want to reset your account balance to $10,000?")) {
      socketRef.current.emit("reset_account");
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>Trading Dashboard {isConnected ? "🟢" : "🔴"}</h2>
      
      {/* Control Panel */}
      <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <button onClick={toggleDemoMode} style={{ padding: '10px 15px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '5px' }}>
          {tradingStatus.demo_mode ? "Switch to Real" : "Switch to Demo"}
        </button>
        
        <select 
          onChange={(e) => setRiskLevel(parseFloat(e.target.value))} 
          value={tradingStatus.risk_level || 0.02}
          style={{ padding: '10px', borderRadius: '5px' }}
        >
          <option value={0.01}>1% Risk</option>
          <option value={0.02}>2% Risk</option>
          <option value={0.03}>3% Risk</option>
          <option value={0.05}>5% Risk</option>
        </select>
        
        <button onClick={closeAllPositions} style={{ padding: '10px 15px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '5px' }}>
          Close All Positions
        </button>

        <button onClick={resetAccount} style={{ padding: '10px 15px', background: '#f59e0b', color: 'white', border: 'none', borderRadius: '5px' }}>
          Reset Account
        </button>
      </div>

      {/* Performance Overview */}
      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <div style={{ padding: '15px', background: '#f3f4f6', borderRadius: '8px', flex: 1, minWidth: '200px' }}>
          <h3>💰 Performance</h3>
          <p>Profit: <span style={{ color: performance.profit >= 0 ? '#10b981' : '#ef4444' }}>
            ${performance.profit.toFixed(2)}
          </span></p>
          <p>Trades: {performance.trades}</p>
          <p>Win Rate: {performance.winRate.toFixed(1)}%</p>
          <p>Wins: {performance.wins} | Losses: {performance.losses}</p>
        </div>
        
        <div style={{ padding: '15px', background: '#f3f4f6', borderRadius: '8px', flex: 1, minWidth: '200px' }}>
          <h3>⚙️ Status</h3>
          <p>Mode: <strong>{tradingStatus.demo_mode ? "DEMO" : "REAL"}</strong></p>
          <p>Balance: <strong>${tradingStatus.balance?.toFixed(2) || '0.00'}</strong></p>
          <p>Equity: <strong>${tradingStatus.equity?.toFixed(2) || '0.00'}</strong></p>
          <p>Risk: <strong>{(tradingStatus.risk_level * 100)?.toFixed(1) || '2.0'}%</strong></p>
          <p>Open Positions: <strong>{tradingStatus.open_positions || 0}</strong></p>
          {tradingStatus.consecutive_losses > 0 && (
            <p style={{ color: '#ef4444', fontWeight: 'bold' }}>
              Consecutive Losses: {tradingStatus.consecutive_losses}
            </p>
          )}
        </div>
      </div>

      {/* Chart */}
      <div ref={chartContainerRef} style={{ 
        width: "100%", 
        height: "400px",
        border: "1px solid #e5e7eb",
        borderRadius: "8px",
        marginBottom: '20px'
      }} />
      
      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
        <button 
          onClick={() => setActiveTab("signals")} 
          style={{ 
            padding: '10px 15px', 
            background: activeTab === "signals" ? '#3b82f6' : '#e5e7eb', 
            color: activeTab === "signals" ? 'white' : '#374151',
            border: 'none', 
            borderRadius: '5px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          📊 Signals
        </button>
        <button 
          onClick={() => setActiveTab("positions")} 
          style={{ 
            padding: '10px 15px', 
            background: activeTab === "positions" ? '#3b82f6' : '#e5e7eb', 
            color: activeTab === "positions" ? 'white' : '#374151',
            border: 'none', 
            borderRadius: '5px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          📈 Positions ({openPositions.length})
        </button>
        <button 
          onClick={() => setActiveTab("history")} 
          style={{ 
            padding: '10px 15px', 
            background: activeTab === "history" ? '#3b82f6' : '#e5e7eb', 
            color: activeTab === "history" ? 'white' : '#374151',
            border: 'none', 
            borderRadius: '5px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          📋 History ({tradeHistory.length})
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "signals" && (
        <div style={{ padding: '15px', background: '#f3f4f6', borderRadius: '8px', minHeight: '200px' }}>
          <h3>📊 Recent Signals</h3>
          {signals.length === 0 ? (
            <p style={{ color: '#6b7280', textAlign: 'center', padding: '40px' }}>
              No signals yet. Waiting for market data...
            </p>
          ) : (
            signals.slice().reverse().map((signal, index) => (
              <div key={index} style={{ 
                padding: '12px', 
                margin: '10px 0', 
                background: signal.signal === 'buy' ? '#dcfce7' : signal.signal === 'sell' ? '#fee2e2' : '#fef3c7',
                borderRadius: '8px',
                border: '2px solid',
                borderColor: signal.signal === 'buy' ? '#10b981' : signal.signal === 'sell' ? '#ef4444' : '#f59e0b'
              }}>
                <div style={{ fontSize: '1.1em', fontWeight: 'bold', marginBottom: '8px' }}>
                  {signal.signal?.toUpperCase()} - {signal.reason}
                </div>
                <div style={{ fontSize: '0.9em', color: '#4b5563' }}>
                  Confidence: <strong>{signal.confidence?.toFixed(1)}%</strong> | 
                  RSI: <strong>{signal.rsi?.toFixed(1)}</strong> | 
                  Price: <strong>{signal.current_price?.toFixed(5)}</strong>
                </div>
                <div style={{ fontSize: '0.8em', color: '#6b7280', marginTop: '5px' }}>
                  {new Date(signal.timestamp * 1000).toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "positions" && (
        <div style={{ padding: '15px', background: '#f3f4f6', borderRadius: '8px', minHeight: '200px' }}>
          <h3>📈 Open Positions ({openPositions.length})</h3>
          {openPositions.length === 0 ? (
            <p style={{ color: '#6b7280', textAlign: 'center', padding: '40px' }}>
              No open positions
            </p>
          ) : (
            openPositions.map(pos => (
              <div key={pos.id} style={{ 
                padding: '12px', 
                margin: '10px 0', 
                background: pos.direction === 'buy' ? '#dcfce7' : '#fee2e2',
                borderRadius: '8px',
                border: '2px solid',
                borderColor: pos.direction === 'buy' ? '#10b981' : '#ef4444'
              }}>
                <div style={{ fontSize: '1.1em', fontWeight: 'bold', marginBottom: '8px' }}>
                  {pos.direction.toUpperCase()} - ${pos.amount?.toFixed(2)}
                </div>
                <div style={{ fontSize: '0.9em', color: '#4b5563' }}>
                  Entry: <strong>{pos.entry_price?.toFixed(5)}</strong>
                </div>
                <div style={{ fontSize: '0.9em', color: '#4b5563' }}>
                  Reason: {pos.signal_reason}
                </div>
                <div style={{ fontSize: '0.9em', color: '#4b5563' }}>
                  Confidence: <strong>{pos.confidence?.toFixed(1)}%</strong>
                </div>
                <div style={{ fontSize: '0.8em', color: '#6b7280', marginTop: '5px' }}>
                  ID: {pos.id}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "history" && (
        <div style={{ padding: '15px', background: '#f3f4f6', borderRadius: '8px', minHeight: '200px' }}>
          <h3>📋 Trade History ({tradeHistory.length})</h3>
          <div style={{ marginBottom: '15px', padding: '10px', background: '#e5e7eb', borderRadius: '5px' }}>
            <strong>Win Rate: {calculateWinRate(tradeHistory).toFixed(1)}%</strong>
          </div>
          {tradeHistory.length === 0 ? (
            <p style={{ color: '#6b7280', textAlign: 'center', padding: '40px' }}>
              No trade history yet
            </p>
          ) : (
            tradeHistory.slice().reverse().map((trade, index) => (
              <div key={index} style={{ 
                padding: '12px', 
                margin: '10px 0', 
                background: trade.profit_loss > 0 ? '#dcfce7' : '#fee2e2',
                borderRadius: '8px',
                border: '2px solid',
                borderColor: trade.profit_loss > 0 ? '#10b981' : '#ef4444'
              }}>
                <div style={{ fontSize: '1.1em', fontWeight: 'bold', marginBottom: '8px' }}>
                  {trade.direction?.toUpperCase()} - 
                  P/L: <span style={{ color: trade.profit_loss > 0 ? '#10b981' : '#ef4444' }}>
                    ${trade.profit_loss?.toFixed(2)}
                  </span>
                </div>
                <div style={{ fontSize: '0.9em', color: '#4b5563' }}>
                  Entry: <strong>{trade.entry_price?.toFixed(5)}</strong> | 
                  Exit: <strong>{trade.exit_price?.toFixed(5)}</strong>
                </div>
                <div style={{ fontSize: '0.9em', color: '#4b5563' }}>
                  Reason: {trade.signal_reason}
                </div>
                <div style={{ fontSize: '0.8em', color: '#6b7280', marginTop: '5px' }}>
                  {new Date(trade.timestamp * 1000).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}