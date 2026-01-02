# utils/indicators.py
import numpy as np
from typing import List, Dict, Tuple

# ─────────────────────────────────────────────
def calculate_rsi(closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0

    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = max(np.mean(losses[:period]), 1e-10)

    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


# ─────────────────────────────────────────────
def calculate_ema(closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period:
        return float(closes[-1]) if len(closes) else 0.0

    alpha = 2 / (period + 1)
    ema = closes[0]

    for price in closes:
        ema = alpha * price + (1 - alpha) * ema

    return float(ema)


# ─────────────────────────────────────────────
def calculate_support_resistance(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    lookback_period: int = 20
) -> Dict[str, float]:

    if len(closes) < lookback_period:
        return {}

    recent_highs = highs[-lookback_period:]
    recent_lows = lows[-lookback_period:]
    price = closes[-1]

    resistance = max(recent_highs)
    support = min(recent_lows)

    result = {}
    if support < price:
        result["support"] = float(support)
    if resistance > price:
        result["resistance"] = float(resistance)

    return result


# ─────────────────────────────────────────────
def calculate_bollinger_bands(
    closes: np.ndarray,
    period: int = 20,
    num_std: float = 2.0
) -> Tuple[float, float, float]:

    if len(closes) < period:
        last = closes[-1] if len(closes) else 0.0
        return last, last, last

    sma = np.mean(closes[-period:])
    std = np.std(closes[-period:])

    return (
        float(sma + num_std * std),
        float(sma - num_std * std),
        float(sma)
    )


# ─────────────────────────────────────────────
def calculate_adx(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    period: int = 14
) -> float:

    if len(closes) < period + 1:
        return 0.0

    tr = np.maximum(
        highs[1:] - lows[1:],
        np.abs(highs[1:] - closes[:-1]),
        np.abs(lows[1:] - closes[:-1])
    )

    plus_dm = np.maximum(highs[1:] - highs[:-1], 0.0)
    minus_dm = np.maximum(lows[:-1] - lows[1:], 0.0)

    atr = np.mean(tr[-period:])
    if atr == 0:
        return 0.0

    plus_di = 100 * np.mean(plus_dm[-period:]) / atr
    minus_di = 100 * np.mean(minus_dm[-period:]) / atr

    dx = abs(plus_di - minus_di) / max(plus_di + minus_di, 1e-10)
    return float(100 * dx)


# ─────────────────────────────────────────────
def calculate_volatility(closes: np.ndarray, period: int = 20) -> float:
    if len(closes) < period:
        return 0.0
    returns = np.diff(np.log(closes))
    return float(np.std(returns[-period:]))


# ─────────────────────────────────────────────
def calculate_common_indicators(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray
) -> Dict[str, float]:

    print(f"[INDICATORS] Calculating with {len(closes)} closes")

    indicators = {
        "rsi": calculate_rsi(closes),
        "adx": calculate_adx(highs, lows, closes),
        "sma_fast": calculate_ema(closes, 9),
        "sma_slow": calculate_ema(closes, 21),
        "volatility": calculate_volatility(closes)
    }

    upper, lower, mid = calculate_bollinger_bands(closes)
    indicators.update({
        "bb_upper": upper,
        "bb_lower": lower,
        "bb_middle": mid
    })

    indicators.update(
        calculate_support_resistance(highs, lows, closes, 30)
    )

    return indicators


# ─────────────────────────────────────────────
# HTF SUPPORT
def adx_from_candles(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> float:

    if len(closes) < period + 1:
        return 25.0

    highs = np.array(highs[-(period + 20):])
    lows = np.array(lows[-(period + 20):])
    closes = np.array(closes[-(period + 20):])

    return calculate_adx(highs, lows, closes, period)
