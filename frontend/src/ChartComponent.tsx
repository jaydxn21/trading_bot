// src/ChartComponent.tsx
import React, { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  LineData,
  HistogramData,
} from "lightweight-charts";

interface Props {
  candleData: any[];
  showVolume: boolean;
  showSMA: boolean;
  showRSI: boolean;
}

export default function ChartComponent({ candleData, showVolume, showSMA, showRSI }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<Map<string, ISeriesApi<any>>>(new Map());

  useEffect(() => {
    if (!ref.current) return;

    chart.current = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 500,
      layout: {
        background: { type: ColorType.Solid, color: "#0a0a0a" },
        textColor: "#aaa",
      },
      grid: { vertLines: { color: "#1a1a1a" }, horzLines: { color: "#1a1a1a" } },
      timeScale: { borderColor: "#333", timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: "#333" },
      crosshair: { mode: 1 },
    });

    // Candlesticks
    series.current.set(
      "candle",
      chart.current.addCandlestickSeries({
        upColor: "#00c853",
        downColor: "#ff1744",
        borderVisible: false,
        wickUpColor: "#00c853",
        wickDownColor: "#ff1744",
      })
    );

    // Volume
    series.current.set(
      "volume",
      chart.current.addHistogramSeries({
        color: "#00d4ff",
        priceScaleId: "",
        priceFormat: { type: "volume" },
      })
    );
    series.current.get("volume")!.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    // SMA
    series.current.set("sma", chart.current.addLineSeries({ color: "#00d4ff", lineWidth: 2 }));

    // RSI
    series.current.set(
      "rsi",
      chart.current.addLineSeries({
        color: "#ff9100",
        lineWidth: 2,
        priceScaleId: "rsi",
      })
    );
    chart.current.priceScale("rsi").applyOptions({
      scaleMargins: { top: 0.1, bottom: 0.9 },
      visible: showRSI,
    });

    const resize = () => chart.current!.applyOptions({ width: ref.current!.clientWidth });
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chart.current?.remove();
    };
  }, []);

  useEffect(() => {
    if (!chart.current || candleData.length === 0) return;

    // CONVERT STRINGS → NUMBERS
    const formatted: CandlestickData[] = candleData.map((c: any) => ({
      time: c.time,
      open: parseFloat(c.open),
      high: parseFloat(c.high),
      low: parseFloat(c.low),
      close: parseFloat(c.close),
    }));

    const candle = series.current.get("candle")!;
    candle.setData(formatted);

    // VOLUME
    if (showVolume) {
      const volData: HistogramData[] = candleData.map((c: any) => ({
        time: c.time,
        value: Math.abs(parseFloat(c.close) - parseFloat(c.open)) * 1500,
        color: parseFloat(c.close) > parseFloat(c.open) ? "rgba(0,200,83,0.6)" : "rgba(255,23,68,0.6)",
      }));
      series.current.get("volume")!.setData(volData);
    }
    series.current.get("volume")!.applyOptions({ visible: showVolume });

    // SMA
    if (showSMA && candleData.length >= 20) {
      const closes = candleData.map((c: any) => parseFloat(c.close));
      const sma20: LineData[] = closes
        .map((_, i) => {
          if (i < 19) return null;
          const sum = closes.slice(i - 19, i + 1).reduce((a, b) => a + b, 0);
          return { time: candleData[i].time, value: sum / 20 };
        })
        .filter(Boolean) as LineData[];
      series.current.get("sma")!.setData(sma20);
    }
    series.current.get("sma")!.applyOptions({ visible: showSMA });

    // RSI (REAL CALCULATION)
    if (showRSI && candleData.length >= 14) {
      const closes = candleData.map((c: any) => parseFloat(c.close));
      const rsi14: LineData[] = [];
      let gains = 0;
      let losses = 0;

      for (let i = 1; i < closes.length; i++) {
        const diff = closes[i] - closes[i - 1];
        if (i === 14) {
          gains /= 14;
          losses /= 14;
        }
        if (diff > 0) gains += diff;
        else losses -= diff;

        if (i >= 14) {
          const avgGain = gains / 14;
          const avgLoss = losses / 14;
          const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
          const rsi = 100 - 100 / (1 + rs);
          rsi14.push({ time: candleData[i].time, value: rsi });

          // Smooth for next
          gains = (gains - gains / 14) + (diff > 0 ? diff : 0);
          losses = (losses - losses / 14) + (diff < 0 ? -diff : 0);
        }
      }
      series.current.get("rsi")!.setData(rsi14);
    }
    series.current.get("rsi")!.applyOptions({ visible: showRSI });

    chart.current.timeScale().fitContent();
  }, [candleData, showVolume, showSMA, showRSI]);

  return <div ref={ref} style={{ width: "100%", height: 500 }} />;
}