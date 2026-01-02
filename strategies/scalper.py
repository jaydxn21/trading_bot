import logging
from .base_strategies import BaseStrategy

logger = logging.getLogger(__name__)

class ScalperStrategy(BaseStrategy):
    def __init__(self, config=None):
        super().__init__("scalper", config or {})

    def analyze_market(self, candles, current_price, indicators, htf_context=None):
        self.ingest_htf_context(htf_context)
        rsi = indicators.get("rsi", 50)
        adx = indicators.get("adx", 0)
        sma_fast = indicators.get("sma_fast")
        sma_slow = indicators.get("sma_slow")
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")

        signal = "hold"
        confidence = 0

        # ───────── Direction (PRIMARY) ─────────
        if sma_fast and sma_slow:
            if sma_fast > sma_slow:
                signal = "buy"
                confidence = 25
            elif sma_fast < sma_slow:
                signal = "sell"
                confidence = 25
            else:
                return {"signal": "hold", "confidence": 0}

        # ───────── RSI CONFIRMATION ─────────
        if signal == "buy":
            if rsi < 50:
                confidence += 20
            elif rsi > 65:
                confidence -= 10
        else:
            if rsi > 50:
                confidence += 20
            elif rsi < 35:
                confidence -= 10

        # ───────── ADX (NON-BLOCKING) ─────────
        if adx >= 12:
            confidence += 15
        elif adx < 8:
            confidence -= 5

        # ───────── BOLLINGER POSITION ─────────
        if bb_upper and bb_lower and bb_upper != bb_lower:
            pos = (current_price - bb_lower) / (bb_upper - bb_lower)

            if signal == "buy" and pos <= 0.45:
                confidence += 10
            elif signal == "sell" and pos >= 0.55:
                confidence += 10

        # ───────── HTF ALIGNMENT (SOFT BONUS) ─────────
        if htf_context:
            hf = htf_context.get("htf_sma_fast")
            hs = htf_context.get("htf_sma_slow")

            if hf and hs:
                if signal == "buy" and hf > hs:
                    confidence += 10
                elif signal == "sell" and hf < hs:
                    confidence += 10

        confidence = max(10, min(90, confidence))

        logger.info(
            f"[SCALPER] {signal.upper()} @ {current_price:.2f} | "
            f"RSI={rsi:.1f} ADX={adx:.1f} CONF={confidence}%"
        )

        return {
            "signal": signal,
            "confidence": int(confidence),
            "price": current_price,
            "strategy": "scalper"
        }
