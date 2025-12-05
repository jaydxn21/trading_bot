import React, { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  LineData,
  HistogramData,
  UTCTimestamp,
  IPriceLine,
} from "lightweight-charts";

interface Props {
  candleData: any[];
  showVolume: boolean;
  showSMA: boolean;
  showRSI: boolean;
  currentPrice?: number | null;
}

export default function ChartComponent({
  candleData,
  showVolume,
  showSMA,
  showRSI,
  currentPrice,
}: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<Map<string, ISeriesApi<any>>>(new Map());
  const priceLineRef = useRef<IPriceLine | null>(null);

  // Create chart once
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { type: ColorType.Solid, color: "#0a0a0a" },
        textColor: "#d1d4dc",
      },
      grid: {
        vertLines: { color: "#1f1f2e" },
        horzLines: { color: "#1f1f2e" },
      },
      crosshair: { mode: 1 },
      timeScale: {
        borderColor: "#333",
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: { borderColor: "#333" },
    });

    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#00ff9d",
      downColor: "#ff1744",
      borderVisible: false,
      wickUpColor: "#00ff9d",
      wickDownColor: "#ff1744",
    });
    seriesRef.current.set("candle", candleSeries);

    const volumeSeries = chart.addHistogramSeries({
      color: "#26a69a",
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });
    seriesRef.current.set("volume", volumeSeries);

    const smaSeries = chart.addLineSeries({
      color: "#00d4ff",
      lineWidth: 2,
    });
    seriesRef.current.set("sma", smaSeries);

    const rsiSeries = chart.addLineSeries({
      color: "#ff9100",
      lineWidth: 2,
      priceScaleId: "rsi",
    });
    chart.priceScale("rsi").applyOptions({
      scaleMargins: { top: 0.1, bottom: 0.9 },
    });
    seriesRef.current.set("rsi", rsiSeries);

    rsiSeries.createPriceLine({ price: 70, color: "#ff1744", lineWidth: 1, lineStyle: 2 });
    rsiSeries.createPriceLine({ price: 30, color: "#00c853", lineWidth: 1, lineStyle: 2 });

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, []);

  // Update data
  useEffect(() => {
    if (!chartRef.current || candleData.length === 0) return;

    const candleSeries = seriesRef.current.get("candle")!;

    // Candles
    const formattedCandles: CandlestickData[] = candleData.map((c: any) => ({
      time: c.time as UTCTimestamp,
      open: parseFloat(c.open),
      high: parseFloat(c.high),
      low: parseFloat(c.low),
      close: parseFloat(c.close),
    }));
    candleSeries.setData(formattedCandles);

    // Volume
    const volData: HistogramData[] = candleData.map((c: any) => {
      const open = parseFloat(c.open);
      const close = parseFloat(c.close);
      return {
        time: c.time as UTCTimestamp,
        value: Math.abs(close - open) * 1800,
        color: close >= open ? "rgba(0, 255, 157, 0.5)" : "rgba(255, 23, 68, 0.5)",
      };
    });
    seriesRef.current.get("volume")!.setData(volData);
    seriesRef.current.get("volume")!.applyOptions({ visible: showVolume });

    // SMA20
    if (showSMA && candleData.length >= 20) {
      const closes = candleData.map((c) => parseFloat(c.close));
      const smaData: LineData[] = closes.slice(19).map((_, i) => {
        const sum = closes.slice(i, i + 20).reduce((a, b) => a + b, 0);
        return {
          time: candleData[i + 19].time as UTCTimestamp,
          value: sum / 20,
        };
      });
      seriesRef.current.get("sma")!.setData(smaData);
    }
    seriesRef.current.get("sma")!.applyOptions({ visible: showSMA });

    // RSI14 (Wilder)
    if (showRSI && candleData.length >= 15) {
      const closes = candleData.map((c) => parseFloat(c.close));
      const rsiData: LineData[] = [];
      let avgGain = 0;
      let avgLoss = 0;

      for (let i = 1; i < closes.length; i++) {
        const diff = closes[i] - closes[i - 1];
        const gain = diff > 0 ? diff : 0;
        const loss = diff < 0 ? -diff : 0;

        if (i === 14) {
          avgGain = gain / 14;
          avgLoss = loss / 14;
        } else if (i > 14) {
          avgGain = (avgGain * 13 + gain) / 14;
          avgLoss = (avgLoss * 13 + loss) / 14;
        }

        if (i >= 14) {
          const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
          const rsiVal = avgLoss === 0 ? 100 : 100 - 100 / (1 + rs);
          rsiData.push({
            time: candleData[i].time as UTCTimestamp,
            value: rsiVal,
          });
        }
      }
      seriesRef.current.get("rsi")!.setData(rsiData);
    }
    seriesRef.current.get("rsi")!.applyOptions({ visible: showRSI });

    // Live Price Line — only if valid
    if (priceLineRef.current) {
      candleSeries.removePriceLine(priceLineRef.current);
      priceLineRef.current = null;
    }

    if (typeof currentPrice === "number" && !isNaN(currentPrice)) {
      priceLineRef.current = candleSeries.createPriceLine({
        price: currentPrice,
        color: "#00ffff",
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        axisLabelColor: "#000",
        axisLabelTextColor: "#00ffff",
        title: "LIVE",
      });
    }

    chartRef.current!.timeScale().fitContent();
  }, [candleData, showVolume, showSMA, showRSI, currentPrice]);

  return (
    <div
      ref={chartContainerRef}
      style={{ width: "100%", height: "500px", position: "relative" }}
    />
  );
}