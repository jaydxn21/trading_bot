// src/components/TradingDashboard.js
import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';

export default function TradingDashboard() {
  const chartContainerRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const [ws, setWs] = useState(null);

  // Account state
  const [balance, setBalance] = useState(10000);
  const [openPnL, setOpenPnL] = useState(0);
  const [equity, setEquity] = useState(10000);
  const [lastPrice, setLastPrice] = useState(null);

  // Trades
  const [openTrades, setOpenTrades] = useState([]);
  const entryLinesRef = useRef([]);

  // Trade input refs
  const lotRef = useRef();
  const tpRef = useRef();
  const slRef = useRef();

  // --- Chart & WebSocket setup ---
  useEffect(() => {
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: { backgroundColor: '#fff', textColor: '#000' },
      grid: { vertLines: { color: '#eee' }, horzLines: { color: '#eee' } },
      crosshair: { mode: 1 },
      priceScale: { borderVisible: true },
      timeScale: { borderVisible: true, timeVisible: true },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });
    candleSeriesRef.current = candleSeries;

    const handleResize = () =>
      chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    window.addEventListener('resize', handleResize);

    // WebSocket
    const socket = new WebSocket('ws://localhost:5000'); // adjust as needed
    setWs(socket);
    let currentCandle = null;

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // Live tick for candle
      if (data.tick) {
        const tick = data.tick;
        const timestamp = Math.floor(tick.epoch / 60) * 60;
        const price = tick.quote;

        if (!currentCandle || currentCandle.time !== timestamp) {
          currentCandle = { time: timestamp, open: price, high: price, low: price, close: price };
          candleSeries.update(currentCandle);
        } else {
          currentCandle.high = Math.max(currentCandle.high, price);
          currentCandle.low = Math.min(currentCandle.low, price);
          currentCandle.close = price;
          candleSeries.update(currentCandle);
        }
        setLastPrice(price);
      }

      // Account snapshot
      if (data.account) {
        const snap = data.account;
        setBalance(snap.balance);
        setEquity(snap.equity);
        setOpenPnL(snap.open_pnl);
        setOpenTrades(snap.open_trades || []);
        if (snap.last_price != null) setLastPrice(snap.last_price);
      }
    };

    return () => {
      socket.close();
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  // --- Draw trade overlays ---
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    entryLinesRef.current.forEach((line) =>
      candleSeriesRef.current.removePriceLine(line)
    );
    entryLinesRef.current = [];

    openTrades.forEach((trade) => {
      const entryLine = candleSeriesRef.current.createPriceLine({
        price: trade.entry,
        color: trade.type === 'BUY' ? '#26a69a' : '#ef5350',
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'Entry',
      });
      entryLinesRef.current.push(entryLine);

      if (trade.take_profit != null) {
        const tpLine = candleSeriesRef.current.createPriceLine({
          price: trade.take_profit,
          color: '#3498db',
          lineWidth: 1,
          lineStyle: 3,
          axisLabelVisible: true,
          title: 'TP',
        });
        entryLinesRef.current.push(tpLine);
      }

      if (trade.stop_loss != null) {
        const slLine = candleSeriesRef.current.createPriceLine({
          price: trade.stop_loss,
          color: '#c0392b',
          lineWidth: 1,
          lineStyle: 3,
          axisLabelVisible: true,
          title: 'SL',
        });
        entryLinesRef.current.push(slLine);
      }
    });
  }, [openTrades]);

  // --- Trade actions ---
  const placeTrade = (side) => {
    if (!lastPrice) return alert('No price yet');
    const lot = parseFloat(lotRef.current.value) || 1;
    const tp =
      tpRef.current.value.trim() === '' ? null : parseFloat(tpRef.current.value);
    const sl =
      slRef.current.value.trim() === '' ? null : parseFloat(slRef.current.value);

    if (ws)
      ws.send(
        JSON.stringify({
          type: 'new_trade',
          symbol: 'R_100',
          tradeType: side,
          entry: lastPrice,
          lot,
          take_profit: tp,
          stop_loss: sl,
        })
      );
  };

  const closeTrade = (id) => {
    if (ws && lastPrice != null)
      ws.send(JSON.stringify({ type: 'close_trade', id, price: lastPrice }));
  };

  return (
    <div className="p-4 flex flex-col gap-4">
      {/* Account Summary */}
      <div className="grid grid-cols-3 gap-4 text-center bg-gray-100 rounded p-4 shadow">
        <div>
          <p className="text-lg font-bold">Balance</p>
          <p>${balance.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-lg font-bold">PnL</p>
          <p style={{ color: openPnL >= 0 ? 'green' : 'red' }}>
            {openPnL.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-lg font-bold">Last Price</p>
          <p>{lastPrice ? lastPrice.toFixed(5) : '-'}</p>
        </div>
      </div>

      {/* Trade Controls */}
      <div className="bg-white p-4 rounded shadow flex flex-col gap-2">
        <div className="flex gap-4 flex-wrap">
          <label>
            Lot Size:{' '}
            <input
              ref={lotRef}
              type="number"
              defaultValue={1}
              min={0.01}
              step={0.01}
              className="border px-2 rounded w-24"
            />
          </label>
          <label>
            TP:{' '}
            <input
              ref={tpRef}
              type="number"
              placeholder="Take Profit"
              className="border px-2 rounded w-24"
            />
          </label>
          <label>
            SL:{' '}
            <input
              ref={slRef}
              type="number"
              placeholder="Stop Loss"
              className="border px-2 rounded w-24"
            />
          </label>
        </div>
        <div className="flex gap-2 mt-2">
          <button
            onClick={() => placeTrade('BUY')}
            className="bg-green-500 text-white px-4 py-2 rounded flex-1"
          >
            BUY
          </button>
          <button
            onClick={() => placeTrade('SELL')}
            className="bg-red-500 text-white px-4 py-2 rounded flex-1"
          >
            SELL
          </button>
        </div>
      </div>

      {/* Chart */}
      <div
        ref={chartContainerRef}
        className="w-full border rounded shadow"
        style={{ height: '400px' }}
      />

      {/* Open Trades Table */}
      <div className="bg-white p-4 rounded shadow">
        <h3 className="text-lg font-bold mb-2">Open Trades</h3>
        <table className="w-full text-left border-collapse">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Side</th>
              <th>Entry</th>
              <th>Current</th>
              <th>TP</th>
              <th>SL</th>
              <th>PnL</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {openTrades.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center text-gray-500">
                  No open trades
                </td>
              </tr>
            ) : (
              openTrades.map((trade) => {
                const pnl =
                  trade.type === 'BUY'
                    ? (lastPrice - trade.entry) * trade.lot
                    : (trade.entry - lastPrice) * trade.lot;
                return (
                  <tr key={trade.id}>
                    <td>{trade.symbol}</td>
                    <td>{trade.type}</td>
                    <td>{trade.entry.toFixed(5)}</td>
                    <td>{lastPrice ? lastPrice.toFixed(5) : '-'}</td>
                    <td>{trade.take_profit != null ? trade.take_profit.toFixed(5) : '-'}</td>
                    <td>{trade.stop_loss != null ? trade.stop_loss.toFixed(5) : '-'}</td>
                    <td
                      style={{
                        fontWeight: '600',
                        color: pnl >= 0 ? '#0a7a5a' : '#c0392b',
                      }}
                    >
                      {lastPrice
                        ? pnl >= 0
                          ? `$${pnl.toFixed(2)}`
                          : `-$${Math.abs(pnl).toFixed(2)}`
                        : '$0.00'}
                    </td>
                    <td>
                      <button
                        onClick={() => closeTrade(trade.id)}
                        className="bg-gray-500 text-white px-2 py-1 rounded"
                      >
                        Close
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
