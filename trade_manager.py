# trade_manager.py
import logging
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Callable
from utils.indicators import calculate_common_indicators, adx_from_candles
from config import ACTIVE_STRATEGIES, STRATEGY_CONFIG

logger = logging.getLogger(__name__)

class EnhancedTradingManager:
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
                logger.info(f"[INIT] Strategy {name} disabled in config")
                continue
            strat_instance = self.get_strategy(name)
            if strat_instance:
                self.strategies[name] = strat_instance
                logger.info(f"[INIT] Loaded strategy: {name}")
            else:
                logger.warning(f"[INIT] Strategy {name} not found in loaded strategies")

    def _infer_tf_seconds(self, ltf_candles: List[Dict[str, Any]]) -> int:
        if len(ltf_candles) < 3:
            return 300
        ts = []
        for c in ltf_candles[-50:]:
            t = int(c.get("timestamp", c.get("epoch", 0)))
            if t > 10**12:
                t //= 1000
            ts.append(t)
        diffs = [max(1, ts[i] - ts[i-1]) for i in range(1, len(ts))]
        tf = int(np.median(diffs))
        return max(30, min(tf, 3600 * 4))

    def _create_hourly_candles(self, ltf_candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        hourly = []
        cur_hour = None
        cur_candle = None
        for c in ltf_candles:
            t = int(c.get("timestamp", c.get("epoch", 0)))
            if t > 10**12:
                t //= 1000
            hour_start = t - (t % 3600)
            if cur_hour != hour_start:
                if cur_candle:
                    hourly.append(cur_candle)
                cur_hour = hour_start
                cur_candle = {
                    "timestamp": hour_start,
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"]),
                    "volume": float(c.get("volume", 1.0))
                }
            else:
                cur_candle["high"] = max(cur_candle["high"], float(c["high"]))
                cur_candle["low"] = min(cur_candle["low"], float(c["low"]))
                cur_candle["close"] = float(c["close"])
                cur_candle["volume"] += float(c.get("volume", 1.0))
        if cur_candle and (not hourly or hourly[-1] != cur_candle):
            hourly.append(cur_candle)
        return hourly[-120:]

    def _analyze_ltf_as_htf(self, ltf_candles: List[Dict[str, Any]], tf_sec: int) -> Dict[str, Any]:
        closes = np.array([float(c["close"]) for c in ltf_candles], dtype=float)
        if len(closes) < 20:
            return {"trend": "neutral", "strength": 0, "reason": "Too little LTF data"}
        cph = max(1, int(round(3600 / tf_sec)))
        def scaled(n_hours): return max(3, int(n_hours * cph))
        w_fast = scaled(9); w_slow = scaled(21); w_rsi = scaled(14); w_mom = scaled(8)
        sma_fast = float(np.mean(closes[-w_fast:])) if len(closes) >= w_fast else float(np.mean(closes))
        sma_slow = float(np.mean(closes[-w_slow:])) if len(closes) >= w_slow else float(np.mean(closes))
        if len(closes) >= w_rsi + 1:
            deltas = np.diff(closes[-(w_rsi+1):])
            gains = np.where(deltas > 0, deltas, 0.0)
            losses = np.where(deltas < 0, -deltas, 0.0)
            avg_gain = np.mean(gains) if gains.size else 0.0
            avg_loss = np.mean(losses) if losses.size else 1e-6  # ← FIXED: Removed extra )
            rs = avg_gain / avg_loss if avg_loss != 0 else 0.0
            rsi = float(100.0 - (100.0 / (1.0 + rs))) if avg_loss != 0 else 50.0
        else:
            rsi = 50.0

        trend = "neutral"; strength = 0
        if sma_slow != 0:
            sma_diff_pct = (sma_fast - sma_slow) / sma_slow * 100.0
            if sma_diff_pct > 0.10:
                trend = "bullish"; strength = min(80, abs(sma_diff_pct) * 50)
            elif sma_diff_pct < -0.10:
                trend = "bearish"; strength = min(80, abs(sma_diff_pct) * 50)
        if len(closes) >= w_mom:
            recent = closes[-w_mom:]; mid = len(recent)//2
            first = np.mean(recent[:mid]) if mid>0 else recent[0]
            last = np.mean(recent[mid:]) if mid>0 else recent[-1]
            mom = (last - first) / max(1e-9, first) * 100.0
            if abs(mom) > 0.20:
                if trend == "neutral":
                    trend = "bullish" if mom>0 else "bearish"; strength = 30
                elif (mom>0 and trend=="bullish") or (mom<0 and trend=="bearish"):
                    strength = min(100, strength + 20)
        if rsi > 60 and trend=="bullish": strength = min(100, strength + 10)
        elif rsi < 40 and trend=="bearish": strength = min(100, strength + 10)
        if trend != "neutral" and strength < 20: strength = 20

        self.htf_indicators = {"sma_fast": sma_fast, "sma_slow": sma_slow, "rsi": rsi, "adx": 25.0, "price": float(closes[-1])}
        return {"trend": trend, "strength": int(strength), "sma_fast": sma_fast, "sma_slow": sma_slow, "rsi": rsi, "reason": "LTF-based HTF proxy"}

    def update_higher_timeframe_analysis(self, ltf_candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            if len(ltf_candles) < 30:
                return {"trend": "neutral", "strength": 0, "reason": "Insufficient LTF"}
            tf_sec = self._infer_tf_seconds(ltf_candles)
            hourly = self._create_hourly_candles(ltf_candles)
            if len(hourly) >= 6:
                highs = np.array([c["high"] for c in hourly], dtype=float)
                lows = np.array([c["low"] for c in hourly], dtype=float)
                closes = np.array([c["close"] for c in hourly], dtype=float)
                sma_fast = float(np.mean(closes[-9:])) if len(closes) >= 9 else float(closes[-1])
                sma_slow = float(np.mean(closes[-21:])) if len(closes) >= 21 else float(closes[-1])
                if len(closes) >= 15:
                    deltas = np.diff(closes[-15:])
                    gains = np.where(deltas > 0, deltas, 0.0)
                    losses = np.where(deltas < 0, -deltas, 0.0)
                    avg_gain = np.mean(gains) if gains.size else 0.0
                    avg_loss = np.mean(losses) if losses.size else 1e-6  # ← ALSO FIXED HERE
                    rs = avg_gain / avg_loss if avg_loss != 0 else 0.0
                    rsi_val = float(100.0 - (100.0 / (1.0 + rs))) if avg_loss != 0 else 50.0
                else:
                    rsi_val = 50.0
                adx_val = adx_from_candles(list(highs), list(lows), list(closes), period=14)
                self.htf_indicators = {"sma_fast": sma_fast, "sma_slow": sma_slow, "rsi": rsi_val, "adx": float(adx_val), "price": float(closes[-1])}
                analysis = self._analyze_htf_trend_simple(hourly, self.htf_indicators)
                self.current_htf_trend = analysis["trend"]; self.last_htf_strength = int(analysis.get("strength", 0)); self.htf_candles = hourly
                logger.info(f"[HTF] aggregated hours -> {self.current_htf_trend} {self.last_htf_strength}% ADX:{adx_val:.2f}")
                return analysis
            analysis = self._analyze_ltf_as_htf(ltf_candles, tf_sec)
            self.current_htf_trend = analysis["trend"]; self.last_htf_strength = int(analysis.get("strength", 0))
            logger.info(f"[HTF] LTF proxy -> {self.current_htf_trend} {self.last_htf_strength}%")
            return analysis
        except Exception as e:
            logger.error(f"HTF analysis error: {e}")
            return {"trend": "neutral", "strength": 0, "reason": str(e)}

    def _analyze_htf_trend_simple(self, htf_candles: List[Dict[str, Any]], htf_indicators: Dict[str, Any]) -> Dict[str, Any]:
        if len(htf_candles) < 6:
            return {"trend": "neutral", "strength": 0}
        sma_fast = htf_indicators.get("sma_fast"); sma_slow = htf_indicators.get("sma_slow"); rsi = htf_indicators.get("rsi", 50)
        trend = "neutral"; strength = 0
        if sma_fast is not None and sma_slow is not None and sma_slow != 0:
            sma_diff_percent = (sma_fast - sma_slow) / sma_slow * 100.0
            if sma_diff_percent > 0.1: trend = "bullish"; strength = min(80, abs(sma_diff_percent)*50)
            elif sma_diff_percent < -0.1: trend = "bearish"; strength = min(80, abs(sma_diff_percent)*50)
        if len(htf_candles) >= 8:
            recent = np.array([c["close"] for c in htf_candles[-8:]], dtype=float)
            if len(recent) >= 4:
                first_q = float(np.mean(recent[:4])); last_q = float(np.mean(recent[4:]))
                momentum = (last_q - first_q) / max(1e-9, first_q) * 100.0
                if abs(momentum) > 0.2:
                    if momentum > 0 and trend == "neutral": trend = "bullish"; strength = 30
                    elif momentum < 0 and trend == "neutral": trend = "bearish"; strength = 30
                    elif (momentum > 0 and trend == "bullish") or (momentum < 0 and trend == "bearish"):
                        strength = min(100, strength + 20)
        if rsi > 60 and trend == "bullish": strength = min(100, strength + 10)
        elif rsi < 40 and trend == "bearish": strength = min(100, strength + 10)
        if trend != "neutral" and strength < 20: strength = 20
        return {"trend": trend, "strength": int(strength), "sma_fast": sma_fast, "sma_slow": sma_slow, "rsi": rsi}

    def adjust_signal_with_htf(self, strategy_name: str, signal_data: Dict[str, Any], price: float) -> Dict[str, Any]:
        if signal_data.get("signal") == "hold":
            return signal_data
        original_conf = signal_data.get("confidence", 0)
        signal_type = signal_data["signal"]
        adjustment = 0.0
        if self.current_htf_trend == "bullish":
            if signal_type == "buy":
                adjustment = min(25.0, self.htf_indicators.get("adx", 0.0) / 4.0)
            elif signal_type == "sell":
                adjustment = -min(30.0, self.htf_indicators.get("adx", 0.0) / 3.0)
        elif self.current_htf_trend == "bearish":
            if signal_type == "sell":
                adjustment = min(25.0, self.htf_indicators.get("adx", 0.0) / 4.0)
            elif signal_type == "buy":
                adjustment = -min(30.0, self.htf_indicators.get("adx", 0.0) / 3.0)
        new_conf = max(5, min(95, original_conf + adjustment))
        if adjustment != 0:
            signal_data["confidence"] = int(new_conf)
            logger.info(f"[HTF] {strategy_name} {signal_type}: {original_conf}% -> {new_conf}% (adj {adjustment})")
        return signal_data

    def run_cycle(self, candles: List[Dict[str, Any]], current_price: float) -> Dict[str, Any]:
        try:
            if len(candles) < 30:
                return {"signal": "hold", "confidence": 0, "reason": "Insufficient data"}
            logger.info(f"[CYCLE] Starting analysis with {len(candles)} candles, price: {current_price:.2f}")
            htf_analysis = self.update_higher_timeframe_analysis(candles)
            logger.info(f"[CYCLE] HTF Analysis: {htf_analysis}")

            highs = np.array([c["high"] for c in candles], dtype=float)
            lows = np.array([c["low"] for c in candles], dtype=float)
            closes = np.array([c["close"] for c in candles], dtype=float)
            indicators = calculate_common_indicators(highs, lows, closes)
            indicators["htf_trend"] = htf_analysis.get("trend", "neutral")
            indicators["htf_strength"] = htf_analysis.get("strength", self.last_htf_strength)
            indicators["htf_adx"] = self.htf_indicators.get("adx", 25.0)

            all_signals = []
            for name, strat in self.strategies.items():
                try:
                    sig = strat.analyze_market(candles, current_price, indicators)
                    sig["strategy"] = name
                    sig = self.adjust_signal_with_htf(name, sig, current_price)
                    all_signals.append(sig)
                    logger.info(f"[{name.upper()}] {sig.get('signal')} - {sig.get('confidence')}% - {sig.get('reason', '')}")
                except Exception as e:
                    logger.error(f"Error in strategy {name}: {e}")
                    continue

            best = self._select_best_signal(all_signals, htf_analysis)
            best["htf_trend"] = htf_analysis.get("trend", "neutral")
            best["htf_strength"] = htf_analysis.get("strength", self.last_htf_strength)
            best["timestamp"] = datetime.now().isoformat()
            logger.info(f"[CYCLE] Final: {best.get('signal')} at {best.get('confidence')}% (HTF: {best['htf_trend']} {best['htf_strength']}%)")
            return best
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            return {"signal": "hold", "confidence": 0, "reason": str(e)}

    def _select_best_signal(self, signals: List[Dict[str, Any]], htf_analysis: Dict[str, Any]) -> Dict[str, Any]:
        if not signals:
            return {"signal": "hold", "confidence": 0, "reason": "No signals", "strategy": "none"}
        high = [s for s in signals if s.get("signal") in ["buy", "sell"] and s.get("confidence", 0) >= 70]
        mid = [s for s in signals if s.get("signal") in ["buy", "sell"] and 50 <= s.get("confidence", 0) < 70]
        if high:
            return max(high, key=lambda x: x.get("confidence", 0))
        if mid:
            best = max(mid, key=lambda x: x.get("confidence", 0))
            if htf_analysis.get("strength",0) > 60:
                if ((htf_analysis.get("trend")=="bullish" and best["signal"]=="sell") or (htf_analysis.get("trend")=="bearish" and best["signal"]=="buy")):
                    if best.get("confidence",0) < 60:
                        return {"signal":"hold","confidence":0,"reason":"Counter-trend too weak in strong HTF","strategy":"system"}
            return best
        return {"signal": "hold", "confidence": 0, "reason": "No valid signals above 50%", "strategy": "none"}

    def get_system_summary(self) -> Dict[str, Any]:
        return {
            "portfolio": {"balance": 10000, "equity": 10000, "initialBalance": 10000},
            "open_trades": [],
            "performance": {"total_trades": 0, "win_rate": 0, "total_profit": 0},
            "strategies": {"active": list(self.strategies.keys()), "status": "running"},
            "market_analysis": {
                "htf_trend": self.current_htf_trend,
                "htf_strength": self.last_htf_strength,
                "htf_rsi": self.htf_indicators.get("rsi", 50),
                "htf_adx": self.htf_indicators.get("adx", 25),
                "timestamp": datetime.now().isoformat()
            }
        }