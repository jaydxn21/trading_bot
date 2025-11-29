# strategies/scalper.py
import logging
import numpy as np
from typing import List, Dict, Any
from .base_strategies import BaseStrategy

logger = logging.getLogger(__name__)

class ScalperStrategy(BaseStrategy):
    """Fixed scalping strategy with HTF integration and proper confidence calculation."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("scalper", config or {})
        self.min_confidence = self.config.get('min_confidence', 55)

    def analyze_market(self, candles: List[Dict[str, Any]], price: float, indicators: Dict[str, Any]) -> Dict[str, Any]:
        # Validate indicators first
        if not self.validate_indicators(indicators):
            return {"signal": "hold", "price": price, "confidence": 0, "reason": "Invalid indicators"}
            
        rsi = indicators.get("rsi", 50)
        adx = indicators.get("adx", 0)
        sma_fast = indicators.get("sma_fast")
        sma_slow = indicators.get("sma_slow")
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")

        confidence = 0
        signal = "hold"
        reason = "No clear signal"

        # IMPROVED: Better RSI ranges for scalping
        if rsi < 30:  # More conservative oversold for scalping
            signal = "buy"
            # Base confidence scales with RSI extremity
            base_confidence = 40 + min(25, (30 - rsi))  # 40-65% range
            confidence = base_confidence
            reason = f"Oversold RSI: {rsi:.1f}"
            
        elif rsi > 70:  # More conservative overbought for scalping
            signal = "sell"
            base_confidence = 40 + min(25, (rsi - 70))  # 40-65% range
            confidence = base_confidence
            reason = f"Overbought RSI: {rsi:.1f}"

        if signal != "hold":
            # IMPROVED: SMA analysis - less penalty, more nuanced
            if sma_fast and sma_slow and sma_slow > 0:
                sma_diff_percent = (sma_fast - sma_slow) / sma_slow * 100
                
                # For scalping, we care more about momentum than long-term trend
                if (signal == "buy" and sma_diff_percent > -0.1) or (signal == "sell" and sma_diff_percent < 0.1):
                    # Small difference is acceptable for scalping
                    confidence += 5
                    reason += " + SMA neutral"
                elif (signal == "buy" and sma_diff_percent > 0.05) or (signal == "sell" and sma_diff_percent < -0.05):
                    # Alignment gives bigger bonus
                    confidence += 20
                    reason += " + SMA alignment"
                else:
                    # Only small penalty for contradiction
                    confidence -= 5
                    reason += " + SMA slight contradiction"
            
            # IMPROVED: ADX for scalping - wider optimal range
            if 15 <= adx <= 35:  # Wider optimal range for scalping
                confidence += 15
                reason += " + Good volatility for scalping"
            elif adx > 35:  # Too trending for scalping
                confidence -= 10
                reason += " + High volatility caution"
            elif adx < 15:  # Too flat for scalping
                confidence -= 5
                reason += " + Low volatility"
            
            # Bollinger Band position - strong signal for scalping
            if bb_upper and bb_lower and bb_upper != bb_lower:
                bb_position = (price - bb_lower) / (bb_upper - bb_lower)
                
                if signal == "buy" and bb_position < 0.1:  # Near lower band
                    confidence += 20
                    reason += " + At Bollinger support"
                elif signal == "sell" and bb_position > 0.9:  # Near upper band
                    confidence += 20
                    reason += " + At Bollinger resistance"
                elif signal == "buy" and bb_position < 0.3:  # In lower region
                    confidence += 10
                    reason += " + Near Bollinger support"
                elif signal == "sell" and bb_position > 0.7:  # In upper region
                    confidence += 10
                    reason += " + Near Bollinger resistance"
            
            # Volume confirmation (if available)
            if len(candles) > 1:
                recent_volume = sum(c.get('volume', 1) for c in candles[-5:])
                avg_volume = sum(c.get('volume', 1) for c in candles[-10:-5]) if len(candles) > 10 else recent_volume
                if avg_volume > 0 and recent_volume > avg_volume * 1.2:
                    confidence += 10
                    reason += " + Volume spike"
            
            # Apply HTF trend adjustment
            original_confidence = confidence
            confidence = self.adjust_confidence_with_htf(signal, confidence, price)
            
            # Ensure minimum confidence for trading
            confidence = max(10, min(85, confidence))
            
            logger.info(f"[SCALPER] {signal.upper()} at {price:.2f} - RSI: {rsi:.1f}, "
                       f"ADX: {adx:.1f}, Confidence: {original_confidence:.0f}% → {confidence:.0f}%")

        return {
            "signal": signal,
            "price": price,
            "confidence": int(confidence),
            "reason": reason,
            "strategy": "scalper"
        }