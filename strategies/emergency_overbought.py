# strategies/emergency_overbought.py
import logging
from typing import List, Dict, Any
from .base_strategies import BaseStrategy

logger = logging.getLogger(__name__)

class Emergency_Overbought_Strategy(BaseStrategy):
    """Emergency strategy for extreme RSI conditions with HTF integration."""

    def __init__(self, config: Dict[str, Any] = None, trading_logic=None):
        super().__init__("Emergency_Overbought", config or {})
        self.trading_logic = trading_logic
        self.min_confidence = self.config.get("min_confidence", 10)
        self.rsi_overbought = self.config.get("rsi_overbought_threshold", 85)
        self.rsi_oversold = self.config.get("rsi_oversold_threshold", 15)

    def analyze_market(self, candles: List[Dict[str, Any]], price: float, indicators: Dict[str, Any]) -> Dict[str, Any]:
        if len(candles) < 5:
            return {"signal": "hold", "price": price, "confidence": 0, "reason": "Insufficient data"}
        
        # Validate indicators
        if not self.validate_indicators(indicators):
            return {"signal": "hold", "price": price, "confidence": 0, "reason": "Invalid indicators"}
        
        rsi = indicators.get("rsi", 50)
        adx = indicators.get("adx", 0)
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        resistance = indicators.get("resistance")
        support = indicators.get("support")
        
        confidence = 0
        signal = "hold"
        reason = "No extreme conditions"
        
        logger.info(f"[EMERGENCY] RSI: {rsi:.1f}, ADX: {adx:.1f}, Price: {price:.2f}")
        
        # 🚨 EXTREME OVERBOUGHT - RSI > 85
        if rsi > self.rsi_overbought:
            # Calculate confidence based on RSI extremity
            base_confidence = 35 + min(25, (rsi - self.rsi_overbought))
            
            # Additional confirmations
            confirmations = []
            
            if adx < 15:  # Weak trend favors reversal
                base_confidence += 15
                confirmations.append("weak trend")
            
            if bb_upper and price >= bb_upper * 0.98:
                base_confidence += 10
                confirmations.append("Bollinger upper")
            
            if resistance and price >= resistance * 0.995:
                base_confidence += 10
                confirmations.append("resistance")
            
            confidence = min(75, base_confidence)
            signal = "sell"
            reason = f"EMERGENCY SELL: RSI {rsi:.1f}"
            if confirmations:
                reason += f" + {', '.join(confirmations)}"
            
            logger.warning(f"🚨🚨🚨 EXTREME OVERBOUGHT: RSI {rsi:.1f} -> {confidence}% confidence")
        
        # 🚨 EXTREME OVERSOLD - RSI < 15
        elif rsi < self.rsi_oversold:
            base_confidence = 35 + min(25, (self.rsi_oversold - rsi))
            
            confirmations = []
            
            if adx < 15:
                base_confidence += 15
                confirmations.append("weak trend")
            
            if bb_lower and price <= bb_lower * 1.02:
                base_confidence += 10
                confirmations.append("Bollinger lower")
            
            if support and price <= support * 1.005:
                base_confidence += 10
                confirmations.append("support")
            
            confidence = min(75, base_confidence)
            signal = "buy"
            reason = f"EMERGENCY BUY: RSI {rsi:.1f}"
            if confirmations:
                reason += f" + {', '.join(confirmations)}"
            
            logger.warning(f"🚨🚨🚨 EXTREME OVERSOLD: RSI {rsi:.1f} -> {confidence}% confidence")
        
        # HIGH RSI (70-85) - Warning level
        elif rsi > 70:
            logger.info(f"⚠️ High RSI: {rsi:.1f} (monitoring)")
        
        # Apply HTF adjustment for all signals
        if signal != "hold":
            original_confidence = confidence
            confidence = self.adjust_confidence_with_htf(signal, confidence, price)
            
            # Limit HTF impact on emergency signals
            if abs(confidence - original_confidence) > 15:
                if confidence > original_confidence:
                    confidence = original_confidence + 15
                else:
                    confidence = original_confidence - 15
                    
            logger.info(f"[EMERGENCY] {signal.upper()} - Confidence: {confidence}% - {reason}")
        
        return {
            "signal": signal, 
            "price": price, 
            "confidence": int(confidence), 
            "reason": reason,
            "strategy": "emergency"
        }

    def execute_trade(self, signal: Dict[str, Any], price: float) -> Dict[str, Any]:
        """Execute emergency trade with reduced risk."""
        if signal["signal"] != "hold" and signal.get("confidence", 0) > self.min_confidence:
            # Reduce position size for emergency trades
            original_risk = self.config.get('risk_per_trade', 0.02)
            emergency_risk = original_risk * 0.7  # 30% reduction
            
            # Temporarily set reduced risk
            self.config['risk_per_trade'] = emergency_risk
            
            trade = super().execute_trade(signal, price)
            
            # Restore original risk setting
            self.config['risk_per_trade'] = original_risk
            return trade
        return None

# Add this alias for compatibility
EMERGENCY_Strategy = Emergency_Overbought_Strategy