# trade_logic.py
from typing import Dict, List, Optional, Any
import math

def _sma(values: List[float], n: int) -> Optional[float]:
    if len(values) < n: 
        return None
    return sum(values[-n:]) / n

def _rsi(closes: List[float], n: int = 14) -> Optional[float]:
    if len(closes) < n + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-n, 0):
        diff = closes[i] - closes[i - 1]
        if diff >= 0: gains += diff
        else: losses -= diff
    if losses == 0: 
        return 100.0
    rs = gains / losses
    return 100 - 100 / (1 + rs)

def _atr(candles: List[Dict[str, float]], n: int = 14) -> Optional[float]:
    if len(candles) < n + 1:
        return None
    trs = []
    for i in range(1, n + 1):
        h = candles[-i]["high"]
        l = candles[-i]["low"]
        pc = candles[-i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else None

def evaluate_trades(
    last_price: float,
    open_trades: List[Dict],
    balance: float,
    candles: List[Dict[str, float]],
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Optional[float]]:
    """
    Return:
      {
        'confidence': float (0..100),
        'signal': 'BUY'|'SELL'|None,
        'reason': str,
        'lot': float|None,
        'entry': float|None,
        'sl': float|None,
        'tp': float|None,
        'atr': float|None
      }
    """
    cfg = {
        "fast": 5,
        "slow": 20,
        "rsi_len": 14,
        "atr_len": 14,
        "tp_atr_mult": 0.7,   # TP distance in ATR
        "sl_atr_mult": 0.5,   # SL distance in ATR
        "risk_per_trade": 0.01,  # 1% balance risk (used to compute lot)
        "min_tick_value": 1.0,   # value per point per lot for PnL calc parity (paper)
    }
    if params:
        cfg.update(params)

    if not candles or len(candles) < max(cfg["slow"], cfg["rsi_len"] + 1, cfg["atr_len"] + 1):
        return {"confidence": None, "signal": None, "reason": "not_enough_data", "lot": None, "entry": None, "sl": None, "tp": None, "atr": None}

    closes = [c["close"] for c in candles]
    last = candles[-1]
    prev1 = candles[-2]

    sma_fast = _sma(closes, cfg["fast"])
    sma_slow = _sma(closes, cfg["slow"])
    rsi = _rsi(closes, cfg["rsi_len"])
    atr = _atr(candles, cfg["atr_len"])

    if sma_fast is None or sma_slow is None or rsi is None or atr is None:
        return {"confidence": None, "signal": None, "reason": "indicators_unavailable", "lot": None, "entry": None, "sl": None, "tp": None, "atr": atr}

    # Basic momentum + mean reversion filter for micro scalps
    bias_up = sma_fast > sma_slow
    bias_dn = sma_fast < sma_slow
    bull_body = last["close"] > last["open"]
    bear_body = last["close"] < last["open"]
    pullback_up = bias_up and rsi < 55 and bull_body
    pullback_dn = bias_dn and rsi > 45 and bear_body

    # Confidence components (each adds / subtracts)
    conf = 50.0
    # Trend alignment
    if bias_up: conf += 12
    if bias_dn: conf += 12
    # Candle body direction
    if bull_body: conf += 6
    if bear_body: conf += 6
    # RSI distance from 50 (mild)
    conf += (abs(rsi - 50) / 50.0) * 10  # up to +10
    # Volatility sanity — extremely low ATR means poor edge
    avg_range = sum([c["high"] - c["low"] for c in candles[-5:]]) / 5
    if avg_range <= 0 or atr <= 0:
        conf -= 20
    # Mean reversion pullback boost
    if pullback_up or pullback_dn:
        conf += 8

    # Clamp
    conf = max(0.0, min(100.0, conf))

    signal = None
    reason = "neutral"
    if bias_up and pullback_up:
        signal = "BUY"
        reason = "trend_up_pullback_buy"
    elif bias_dn and pullback_dn:
        signal = "SELL"
        reason = "trend_down_pullback_sell"

    # Build proposed order (paper)
    entry = last_price
    tp = sl = lot = None
    if signal:
        # ATR-based SL/TP
        if signal == "BUY":
            sl = entry - cfg["sl_atr_mult"] * atr
            tp = entry + cfg["tp_atr_mult"] * atr
        else:
            sl = entry + cfg["sl_atr_mult"] * atr
            tp = entry - cfg["tp_atr_mult"] * atr

        # position sizing (very simplified for paper)
        risk_amount = balance * cfg["risk_per_trade"]
        stop_distance = abs(entry - sl)
        if stop_distance > 0:
            lot = max(0.01, round(risk_amount / (stop_distance * cfg["min_tick_value"]), 2))
        else:
            lot = 0.01

    return {
        "confidence": round(conf, 2),
        "signal": signal,
        "reason": reason,
        "lot": lot,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "atr": atr,
    }
