# utils/indicators.py
import numpy as np
from typing import List, Dict, Tuple

# === EXISTING FUNCTIONS (you already have these) ===
def calculate_rsi(closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    down = max(down, 1e-10)
    rs = up / down
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return float(rsi)

def calculate_ema(closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period:
        return float(closes[-1]) if len(closes) > 0 else 0.0
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    ema = np.convolve(closes, weights, mode="full")[:len(closes)]
    return float(ema[-1])

def calculate_support_resistance(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, 
                               lookback_period: int = 20, tolerance: float = 0.002) -> Dict[str, float]:
    if len(closes) < lookback_period:
        return {}
    recent_highs = highs[-lookback_period:]
    recent_lows = lows[-lookback_period:]
    current_price = closes[-1]
    resistance_candidates = []
    support_candidates = []
    for i in range(2, len(recent_highs) - 2):
        if (recent_highs[i] > recent_highs[i-1] and 
            recent_highs[i] > recent_highs[i-2] and 
            recent_highs[i] > recent_highs[i+1] and 
            recent_highs[i] > recent_highs[i+2]):
            resistance_candidates.append(recent_highs[i])
        if (recent_lows[i] < recent_lows[i-1] and 
            recent_lows[i] < recent_lows[i-2] and 
            recent_lows[i] < recent_lows[i+1] and 
            recent_lows[i] < recent_lows[i+2]):
            support_candidates.append(recent_lows[i])
    support_level = None
    resistance_level = None
    if support_candidates:
        below_price = [s for s in support_candidates if s < current_price]
        if below_price:
            support_level = max(below_price)
    if resistance_candidates:
        above_price = [r for r in resistance_candidates if r > current_price]
        if above_price:
            resistance_level = min(above_price)
    result = {}
    if support_level:
        result['support'] = float(support_level)
    if resistance_level:
        result['resistance'] = float(resistance_level)
    return result

def calculate_bollinger_bands(closes: np.ndarray, period: int = 20, num_std: float = 2.0) -> Tuple[float, float, float]:
    if len(closes) < period:
        last_price = closes[-1] if len(closes) > 0 else 0.0
        return last_price, last_price, last_price
    sma = np.mean(closes[-period:])
    std = np.std(closes[-period:])
    upper = sma + num_std * std
    lower = sma - num_std * std
    return float(upper), float(lower), float(sma)

def calculate_adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 0.0
    plus_dm = highs[1:] - highs[:-1]
    minus_dm = lows[:-1] - lows[1:]
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    tr = np.maximum(highs[1:], closes[:-1]) - np.minimum(lows[1:], closes[:-1])
    atr = np.zeros_like(tr)
    atr[period-1] = tr[:period].mean()
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    plus_di = 100 * (np.convolve(plus_dm, np.ones(period), "valid") / atr[period-1:]).mean() / period
    minus_di = 100 * (np.convolve(minus_dm, np.ones(period), "valid") / atr[period-1:]).mean() / period
    dx = 100 * np.abs(plus_di - minus_di) / max((plus_di + minus_di), 1e-10)
    return float(dx)

def calculate_volatility(closes: np.ndarray, period: int = 20) -> float:
    if len(closes) < period:
        return 0.0
    log_returns = np.diff(np.log(closes))
    return float(np.std(log_returns[-period:]))

def calculate_common_indicators(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> Dict[str, float]:
    print(f"[INDICATORS] Calculating with {len(closes)} closes")
    indicators = {}
    indicators["adx"] = calculate_adx(highs, lows, closes, period=14)
    indicators["rsi"] = calculate_rsi(closes, period=14)
    indicators["sma_fast"] = calculate_ema(closes, period=9)
    indicators["sma_slow"] = calculate_ema(closes, period=21)
    upper, lower, middle = calculate_bollinger_bands(closes, period=20, num_std=2.0)
    indicators["bb_upper"] = upper
    indicators["bb_lower"] = lower
    indicators["bb_middle"] = middle
    indicators["volatility"] = calculate_volatility(closes, period=20)
    sr_levels = calculate_support_resistance(highs, lows, closes, lookback_period=30)
    indicators.update(sr_levels)
    return indicators

# === NEW: REQUIRED FOR trade_manager.py ===
def adx_from_candles(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 25.0
    highs = np.array(highs[-period-10:], dtype=float)
    lows = np.array(lows[-period-10:], dtype=float)
    closes = np.array(closes[-period-10:], dtype=float)
    if len(closes) < period + 1:
        return 25.0
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.abs(highs[1:] - closes[:-1]),
        np.abs(lows[1:] - closes[:-1])
    )
    plus_dm = highs[1:] - highs[:-1]
    minus_dm = lows[:-1] - lows[1:]
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)
    atr = np.zeros(len(tr))
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    plus_di = 100 * _wilder_smooth(plus_dm, period) / atr[period-1:]
    minus_di = 100 * _wilder_smooth(minus_dm, period) / atr[period-1:]
    di_sum = plus_di + minus_di
    di_diff = np.abs(plus_di - minus_di)
    dx = np.where(di_sum > 0, 100 * di_diff / di_sum, 0.0)
    adx = np.mean(dx[-period:]) if len(dx) >= period else 25.0
    return float(max(0.0, min(100.0, adx)))

def _wilder_smooth(data: np.ndarray, period: int) -> np.ndarray:
    smoothed = np.zeros(len(data))
    if len(data) == 0:
        return smoothed
    smoothed[period-1] = np.mean(data[:period])
    for i in range(period, len(data)):
        smoothed[i] = (smoothed[i-1] * (period - 1) + data[i]) / period
    return smoothed