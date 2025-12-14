# trade_manager.py — Modular Version with MT5 Bridge + SL/TP
import logging
import time
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Callable
from utils.indicators import calculate_common_indicators, adx_from_candles
from config import ACTIVE_STRATEGIES, STRATEGY_CONFIG
from mt5_bridge import mt5_bridge

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Default SL/TP percentages
DEFAULT_SL_PCT = 0.5   # 0.5% stop loss
DEFAULT_TP_PCT = 1.0   # 1% take profit

class TradingManager:
    def __init__(self, get_strategy_func: Callable[[str], Any]):
        self.get_strategy = get_strategy_func
        self.strategies = {}
        self.htf_candles = []
        self.htf_indicators = {}
        self.current_htf_trend = "neutral"
        self.last_htf_strength = 0
        self.initialize_strategies()

    def initialize_strategies(self):
        for name in ACTIVE_STRATEGIES:
            cfg = STRATEGY_CONFIG.get(name, {})
            if not cfg.get("enabled", True):
                logger.info(f"[INIT] Strategy {name} disabled")
                continue
            strat_instance = self.get_strategy(name)
            if strat_instance:
                self.strategies[name] = strat_instance
                logger.info(f"[INIT] Loaded strategy: {name}")
            else:
                logger.warning(f"[INIT] Strategy {name} not found")

    def update_htf_analysis(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(candles) < 30:
            return {"trend": "neutral", "strength": 0, "reason": "Insufficient data"}

        hourly = self._aggregate_to_hourly(candles)
        closes = np.array([c["close"] for c in hourly], dtype=float)
        sma_fast = float(np.mean(closes[-9:])) if len(closes) >= 9 else closes[-1]
        sma_slow = float(np.mean(closes[-21:])) if len(closes) >= 21 else closes[-1]
        adx_val = adx_from_candles([c["high"] for c in hourly],
                                   [c["low"] for c in hourly],
                                   closes, period=14)

        trend, strength = self._simple_trend_analysis(sma_fast, sma_slow, closes)
        self.htf_indicators = {
            "sma_fast": sma_fast,
            "sma_slow": sma_slow,
            "adx": float(adx_val),
            "price": closes[-1]
        }
        self.current_htf_trend = trend
        self.last_htf_strength = strength
        self.htf_candles = hourly

        return {"trend": trend, "strength": strength}

    def _aggregate_to_hourly(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        hourly = []
        cur_hour, cur_candle = None, None
        for c in candles:
            t = int(c.get("timestamp", c.get("epoch", 0)))
            if t > 1e12:
                t //= 1000
            hour_start = t - (t % 3600)
            if cur_hour != hour_start:
                if cur_candle:
                    hourly.append(cur_candle)
                cur_hour = hour_start
                cur_candle = {
                    "timestamp": hour_start,
                    "open": c["open"],
                    "high": c["high"],
                    "low": c["low"],
                    "close": c["close"],
                    "volume": c.get("volume", 1.0),
                }
            else:
                cur_candle["high"] = max(cur_candle["high"], c["high"])
                cur_candle["low"] = min(cur_candle["low"], c["low"])
                cur_candle["close"] = c["close"]
                cur_candle["volume"] += c.get("volume", 1.0)
        if cur_candle and (not hourly or hourly[-1] != cur_candle):
            hourly.append(cur_candle)
        return hourly[-120:]

    def _simple_trend_analysis(self, sma_fast, sma_slow, closes):
        trend, strength = "neutral", 0
        if sma_slow != 0:
            diff_pct = (sma_fast - sma_slow) / sma_slow * 100
            if diff_pct > 0.1:
                trend = "bullish"; strength = min(80, diff_pct * 50)
            elif diff_pct < -0.1:
                trend = "bearish"; strength = min(80, abs(diff_pct) * 50)
        if len(closes) >= 8:
            recent = closes[-8:]
            mid = len(recent)//2
            first_q, last_q = np.mean(recent[:mid]), np.mean(recent[mid:])
            mom = (last_q - first_q) / max(1e-9, first_q) * 100
            if abs(mom) > 0.2:
                if trend == "neutral":
                    trend = "bullish" if mom>0 else "bearish"
                    strength = 30
                elif (mom>0 and trend=="bullish") or (mom<0 and trend=="bearish"):
                    strength = min(100, strength+20)
        if strength < 20 and trend != "neutral":
            strength = 20
        return trend, int(strength)

    def adjust_signal_with_htf(self, strategy_name: str, signal: Dict[str, Any]) -> Dict[str, Any]:
        if signal.get("signal") == "hold":
            return signal
        adj = 0.0
        sig_type = signal["signal"]
        adx = self.htf_indicators.get("adx", 25.0)
        if self.current_htf_trend == "bullish":
            adj = min(25, adx/4) if sig_type=="buy" else -min(30, adx/3)
        elif self.current_htf_trend == "bearish":
            adj = min(25, adx/4) if sig_type=="sell" else -min(30, adx/3)
        signal["confidence"] = max(5, min(95, signal.get("confidence",0) + adj))
        return signal

    def _select_best_signal(self, signals, htf):
        if not signals:
            return {"signal":"hold","confidence":0,"reason":"No signals","strategy":"none"}
        valid = [s for s in signals if s["signal"] in ["buy","sell"] and s.get("confidence",0)>=50]
        if not valid:
            return {"signal":"hold","confidence":0,"reason":"No signals >=50%","strategy":"none"}
        return max(valid, key=lambda x: x["confidence"])

    def _add_sl_tp(self, signal: Dict[str, Any], price: float) -> Dict[str, Any]:
        """Automatically calculate SL/TP if not already present"""
        action = signal.get("signal", "hold")
        if action == "buy":
            signal["sl_price"] = signal.get("sl_price") or price * (1 - DEFAULT_SL_PCT/100)
            signal["tp_price"] = signal.get("tp_price") or price * (1 + DEFAULT_TP_PCT/100)
        elif action == "sell":
            signal["sl_price"] = signal.get("sl_price") or price * (1 + DEFAULT_SL_PCT/100)
            signal["tp_price"] = signal.get("tp_price") or price * (1 - DEFAULT_TP_PCT/100)
        else:
            signal["sl_price"] = ""
            signal["tp_price"] = ""
        return signal

    def run_cycle(self, candles: List[Dict[str, Any]], current_price: float) -> Dict[str, Any]:
        if len(candles) < 30:
            return {"signal": "hold", "confidence": 0, "reason": "Insufficient candles"}

        htf = self.update_htf_analysis(candles)
        all_signals = []

        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])
        closes = np.array([c["close"] for c in candles])
        indicators = calculate_common_indicators(highs, lows, closes)
        indicators.update({
            "htf_trend": htf["trend"],
            "htf_strength": htf["strength"],
            "htf_adx": self.htf_indicators.get("adx",25.0)
        })

        for name, strat in self.strategies.items():
            try:
                sig = strat.analyze_market(candles, current_price, indicators)
                sig["strategy"] = name
                sig = self.adjust_signal_with_htf(name, sig)
                sig = self._add_sl_tp(sig, current_price)
                all_signals.append(sig)
            except Exception as e:
                logger.error(f"[{name}] Strategy error: {e}")

        best_signal = self._select_best_signal(all_signals, htf)
        best_signal = self._add_sl_tp(best_signal, current_price)
        best_signal["timestamp"] = int(time.time())
        best_signal["action"] = best_signal.get("signal", "hold").upper()
        best_signal["symbol"] = "R_100"

        # SEND SIGNAL TO MT5 BRIDGE — skip HOLD
        if best_signal.get("signal") not in ["hold", "HOLD"]:
            try:
                success = mt5_bridge.write_signal(best_signal)
                if success:
                    logger.info(f"Signal sent to MT5 bridge: {best_signal['action']} {best_signal['symbol']}")
                else:
                    logger.error("Failed to send signal to MT5 bridge")
            except Exception as e:
                logger.error(f"MT5 bridge exception: {e}")
        else:
            logger.info("Best signal is HOLD — not sending to MT5 bridge")

        return best_signal
