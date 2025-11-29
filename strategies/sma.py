# strategies/enhanced_sma.py
import logging
from typing import List, Dict, Any
from .base_strategies import BaseStrategy

logger = logging.getLogger(__name__)

class Enhanced_SMA_Strategy(BaseStrategy):
    """Enhanced SMA strategy optimized for trending markets."""

    def __init__(self, config: Dict[str, Any] = None, trading_logic=None):
        super().__init__("Enhanced_SMA", config or {})
        self.trading_logic = trading_logic
        self.min_confidence = self.config.get('min_confidence', 15)

    def analyze_market(self, candles: List[Dict[str, Any]], price: float, indicators: Dict[str, Any]) -> Dict[str, Any]:
        if not self.validate_indicators(indicators):
            return {"signal": "hold", "price": price, "confidence": 0, "reason": "Invalid indicators"}
            
        sma_fast = indicators.get("sma_fast")
        sma_slow = indicators.get("sma_slow")
        rsi = indicators.get("rsi", 50)
        adx = indicators.get("adx", 0)
        
        if sma_fast is None or sma_slow is None:
            return {"signal": "hold", "price": price, "confidence": 0, "reason": "SMA calculation failed"}

        sma_diff = sma_fast - sma_slow
        sma_diff_percentage = abs(sma_diff) / price * 100
        
        signal = "hold"
        confidence = 0
        reason = "No crossover"
        
        # TRENDING MARKET STRATEGY (ADX > 20)
        if adx > 20:
            logger.info(f"[ENHANCED SMA] Trending market - using trend-following strategy")
            
            # Strong bullish crossover (Fast SMA > Slow SMA by significant margin)
            if sma_fast > sma_slow and sma_diff_percentage > 0.05:
                base_confidence = 30
                
                # RSI adjustment - in trends, we want to avoid overbought/oversold extremes
                if rsi < 70:  # Not extremely overbought
                    rsi_bonus = max(0, 60 - rsi) / 2  # Bonus for lower RSI in uptrend
                    base_confidence += rsi_bonus
                    confidence = min(75, base_confidence)
                    signal = "buy"
                    reason = "Bullish SMA crossover in strong trend"
                else:
                    reason = "Bullish crossover but RSI too high"
            
            # Strong bearish crossover (Fast SMA < Slow SMA by significant margin)
            elif sma_fast < sma_slow and sma_diff_percentage > 0.05:
                base_confidence = 30
                
                if rsi > 30:  # Not extremely oversold
                    rsi_bonus = max(0, rsi - 40) / 2  # Bonus for higher RSI in downtrend
                    base_confidence += rsi_bonus
                    confidence = min(75, base_confidence)
                    signal = "sell"
                    reason = "Bearish SMA crossover in strong trend"
                else:
                    reason = "Bearish crossover but RSI too low"
        
        # RANGING MARKET STRATEGY (ADX < 20)
        else:
            logger.info(f"[ENHANCED SMA] Ranging market - using mean reversion strategy")
            
            # Lower threshold for ranging markets
            if abs(sma_diff_percentage) < 0.02:
                return {"signal": "hold", "price": price, "confidence": 0, "reason": "SMA crossover too weak"}
            
            if sma_fast > sma_slow:
                base_confidence = 20
                # In ranging markets, look for RSI confirmation
                if rsi < 60:
                    base_confidence += 15
                    confidence = min(70, base_confidence)
                    signal = "buy"
                    reason = "Bullish SMA crossover in ranging market"
            
            elif sma_fast < sma_slow:
                base_confidence = 20
                if rsi > 40:
                    base_confidence += 15
                    confidence = min(70, base_confidence)
                    signal = "sell"
                    reason = "Bearish SMA crossover in ranging market"

        if signal != "hold":
            # ADX strength bonus
            adx_bonus = min(15, adx / 2)
            confidence += adx_bonus
            confidence = max(10, min(85, confidence))
            
            # Apply HTF adjustment
            confidence = self.adjust_confidence_with_htf(signal, confidence, price)
            
            logger.info(f"[ENHANCED SMA] {signal.upper()} - Confidence: {confidence:.1f}% - {reason}")

        return {
            "signal": signal,
            "price": price,
            "confidence": int(confidence),
            "reason": reason,
            "strategy": "enhanced_sma"
        }