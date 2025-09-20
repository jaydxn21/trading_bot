# utils/indicators.py
import numpy as np
from typing import Tuple
from typing import Dict



def calculate_rsi(closes: np.ndarray, period: int = 14) -> float:
    """Calculate RSI using closing prices."""
    if len(closes) < period + 1:
        return 50.0  # Neutral if insufficient data

    deltas = np.diff(closes)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    down = max(down, 1e-10)

    rs = up / down
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return float(rsi)


def calculate_ema(closes: np.ndarray, period: int = 14) -> float:
    """Calculate Exponential Moving Average."""
    if len(closes) < period:
        return float(closes[-1]) if len(closes) > 0 else 0.0
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    ema = np.convolve(closes, weights, mode="full")[:len(closes)]
    return float(ema[-1])


def calculate_bollinger_bands(
    closes: np.ndarray, 
    period: int = 20, 
    num_std: float = 2.0
) -> Tuple[float, float, float]:
    """Calculate Bollinger Bands."""
    if len(closes) < period:
        last_price = closes[-1] if len(closes) > 0 else 0.0
        return last_price, last_price, last_price

    sma = np.mean(closes[-period:])
    std = np.std(closes[-period:])
    upper = sma + num_std * std
    lower = sma - num_std * std
    return float(upper), float(lower), float(sma)


def calculate_adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    """Calculate Average Directional Index (ADX)."""
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
    """Calculate simple volatility as std dev of returns."""
    if len(closes) < period:
        return 0.0
    log_returns = np.diff(np.log(closes))
    return float(np.std(log_returns[-period:]))


def calculate_common_indicators(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> Dict[str, float]:
    """
    Compute a set of commonly used indicators for trading strategies.

    Returns a dictionary with:
    - adx
    - rsi
    - sma_fast (EMA 9)
    - sma_slow (EMA 21)
    - upper_band, lower_band, sma_middle (Bollinger Bands 20, 2 std)
    - volatility (20-period)
    """
    indicators = {}

    # ADX
    indicators["adx"] = calculate_adx(highs, lows, closes, period=14)

    # RSI
    indicators["rsi"] = calculate_rsi(closes, period=14)

    # Moving Averages
    indicators["sma_fast"] = calculate_ema(closes, period=9)
    indicators["sma_slow"] = calculate_ema(closes, period=21)

    # Bollinger Bands
    upper, lower, middle = calculate_bollinger_bands(closes, period=20, num_std=2.0)
    indicators["bb_upper"] = upper
    indicators["bb_lower"] = lower
    indicators["bb_middle"] = middle

    # Volatility
    indicators["volatility"] = calculate_volatility(closes, period=20)

    return indicators