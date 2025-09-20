// chartIndicator.js
import { createChart, CrosshairMode } from "lightweight-charts";

export class ChartIndicatorManager {
  constructor(container, initialData = []) {
    this.container = container;
    this.chart = null;
    this.candleSeries = null;
    this.indicators = new Map();
    this.tradeMarkers = new Map();

    this.initChart(initialData);
  }

  initChart(initialData) {
    this.chart = createChart(this.container, {
      width: this.container.clientWidth,
      height: 500,
      layout: { 
        background: { color: "#1f2937" }, 
        textColor: "#d1d5db",
        fontSize: 12
      },
      grid: { 
        vertLines: { color: "#374151", visible: true }, 
        horzLines: { color: "#374151", visible: true } 
      },
      crosshair: { 
        mode: CrosshairMode.Normal,
        vertLine: { 
          color: '#6b7280', 
          width: 1, 
          style: 2, // 2 = Dashed
          labelBackgroundColor: '#374151'
        },
        horzLine: { 
          color: '#6b7280', 
          width: 1, 
          style: 2, // 2 = Dashed
          labelBackgroundColor: '#374151'
        }
      },
      timeScale: { 
        timeVisible: true, 
        secondsVisible: false, 
        barSpacing: 6,
        rightOffset: 10,
        borderColor: '#374151'
      },
      rightPriceScale: { 
        borderColor: '#374151',
        scaleMargins: {
          top: 0.1,
          bottom: 0.2
        }
      },
    });

    this.candleSeries = this.chart.addCandlestickSeries({
      upColor: "#10b981", 
      downColor: "#ef4444",
      borderUpColor: "#10b981", 
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981", 
      wickDownColor: "#ef4444",
      priceFormat: {
        type: 'price',
        precision: 5,
        minMove: 0.00001
      }
    });

    // Set initial data if provided
    if (initialData && initialData.length > 0) {
      this.updateCandles(initialData);
    }
  }

  updateCandles(candles) {
    if (!this.candleSeries || !candles || candles.length === 0) {
      console.warn('Cannot update candles: no candle series or empty data');
      return;
    }

    try {
      // Convert candles to the format expected by Lightweight Charts
      const formatted = candles.map(c => ({
        time: c.time || Math.floor(Date.now() / 1000), // Ensure time is provided
        open: parseFloat(c.open),
        high: parseFloat(c.high),
        low: parseFloat(c.low),
        close: parseFloat(c.close)
      }));
      
      console.log('Setting candle data:', formatted.length, 'candles');
      this.candleSeries.setData(formatted);
      
      // Auto-scroll to the end
      this.chart.timeScale().scrollToPosition(-1, false);
      
    } catch (error) {
      console.error('Error updating candles:', error);
    }
  }

  updateCandle(candle) {
    if (!this.candleSeries || !candle) {
      return;
    }

    try {
      const formattedCandle = {
        time: candle.time || Math.floor(Date.now() / 1000),
        open: parseFloat(candle.open),
        high: parseFloat(candle.high),
        low: parseFloat(candle.low),
        close: parseFloat(candle.close)
      };
      
      this.candleSeries.update(formattedCandle);
    } catch (error) {
      console.error('Error updating single candle:', error);
    }
  }

  addMarker(marker) {
    if (!this.candleSeries) {
      return;
    }

    try {
      const currentMarkers = this.candleSeries.markers() || [];
      const newMarker = {
        time: marker.time || Math.floor(Date.now() / 1000),
        position: marker.position || 'aboveBar',
        color: marker.color || '#3b82f6',
        shape: marker.shape || 'circle',
        text: marker.text || ''
      };
      
      this.candleSeries.setMarkers([...currentMarkers, newMarker]);
    } catch (error) {
      console.error('Error adding marker:', error);
    }
  }

  clearMarkers() {
    if (this.candleSeries) {
      this.candleSeries.setMarkers([]);
    }
  }

  // ... rest of the methods (addIndicator, removeIndicator, etc.) remain the same
  addIndicator(name, type, settings = {}) {
    if (this.indicators.has(name)) {
      return this.indicators.get(name);
    }
    
    let series;
    switch (type) {
      case 'rsi':
        series = this.chart.addLineSeries({
          color: '#3b82f6',
          lineWidth: 2,
          priceScaleId: 'rsi-scale',
          title: name
        });
        this.chart.priceScale('rsi-scale').applyOptions({
          scaleMargins: { top: 0.85, bottom: 0.05 },
          mode: 2, // Percentage
        });
        break;
      case 'ema':
        series = this.chart.addLineSeries({
          color: '#f59e0b',
          lineWidth: 2,
          title: name
        });
        break;
      default:
        console.warn(`Unknown indicator type: ${type}`);
        return null;
    }
    
    this.indicators.set(name, { series, type, settings });
    return series;
  }

  removeIndicator(name) {
    const indicator = this.indicators.get(name);
    if (indicator && indicator.series) {
      this.chart.removeSeries(indicator.series);
    }
    this.indicators.delete(name);
  }

  updateIndicator(name, data) {
    const indicator = this.indicators.get(name);
    if (indicator && indicator.series) {
      indicator.series.setData(data);
    }
  }

  resize() {
    if (this.chart) {
      this.chart.applyOptions({ width: this.container.clientWidth });
      this.chart.timeScale().fitContent();
    }
  }

  destroy() {
    if (this.chart) {
      this.chart.remove();
    }
    this.indicators.clear();
    this.tradeMarkers.clear();
  }
}

// Static calculator methods
ChartIndicatorManager.IndicatorCalculator = {
  calculateRSI: (data, period = 14) => {
    const results = [];
    if (data.length < period + 1) return results;
    
    for (let i = period; i < data.length; i++) {
      let gains = 0;
      let losses = 0;
      
      for (let j = i - period + 1; j <= i; j++) {
        const change = data[j].close - data[j - 1].close;
        if (change >= 0) {
          gains += change;
        } else {
          losses -= change;
        }
      }
      
      const avgGain = gains / period;
      const avgLoss = losses / period;
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      const rsi = 100 - (100 / (1 + rs));
      
      results.push({ time: data[i].time, value: rsi });
    }
    
    return results;
  },
  
  calculateEMA: (data, period = 20) => {
    const results = [];
    if (data.length < period) return results;
    
    // Calculate SMA for first value
    let sum = 0;
    for (let i = 0; i < period; i++) {
      sum += data[i].close;
    }
    let ema = sum / period;
    results.push({ time: data[period - 1].time, value: ema });
    
    // Calculate subsequent EMA values
    const multiplier = 2 / (period + 1);
    for (let i = period; i < data.length; i++) {
      ema = (data[i].close - ema) * multiplier + ema;
      results.push({ time: data[i].time, value: ema });
    }
    
    return results;
  }
};

export default ChartIndicatorManager;