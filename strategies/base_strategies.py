# strategies/base_strategies.py
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Enhanced base strategy with multi-timeframe analysis and proper confidence calculation."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config or {}
        self.capital = self.config.get('capital', 1000)
        self.min_confidence = self.config.get('min_confidence', 50)
        self.htf_trend = None  # Higher timeframe trend
        self.htf_support = None
        self.htf_resistance = None

    def analyze_higher_timeframe(self, htf_candles: List[Dict[str, Any]], htf_indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze 1-hour timeframe for overall trend direction."""
        if not htf_candles or len(htf_candles) < 20:
            return {"trend": "neutral", "strength": 0, "support": None, "resistance": None}
        
        # Use SMA for trend direction
        sma_fast = htf_indicators.get("sma_fast")
        sma_slow = htf_indicators.get("sma_slow")
        htf_rsi = htf_indicators.get("rsi", 50)
        htf_adx = htf_indicators.get("adx", 0)
        
        trend = "neutral"
        strength = 0
        
        if sma_fast and sma_slow and sma_slow > 0:
            # Trend direction
            price_diff_percent = abs(sma_fast - sma_slow) / sma_slow * 100
            
            if sma_fast > sma_slow:
                trend = "bullish"
                strength = min(100, price_diff_percent * 10)  # Scale appropriately
            elif sma_fast < sma_slow:
                trend = "bearish" 
                strength = min(100, price_diff_percent * 10)
        
        # ADX for trend strength
        if htf_adx > 25:
            strength = min(100, strength + (htf_adx - 25))
        
        # Calculate support/resistance from HTF
        support = htf_indicators.get("support")
        resistance = htf_indicators.get("resistance")
        
        analysis = {
            "trend": trend,
            "strength": int(strength),
            "support": support,
            "resistance": resistance,
            "rsi": htf_rsi,
            "adx": htf_adx
        }
        
        self.htf_trend = analysis
        return analysis

    def adjust_confidence_with_htf(self, signal: str, confidence: int, price: float) -> int:
        """Improved HTF confidence adjustment that works with weak trends."""
        if not self.htf_trend:
            return confidence
        
        htf_trend = self.htf_trend.get("trend", "neutral")
        htf_strength = self.htf_trend.get("strength", 0)
        
        # No adjustment for neutral HTF or very weak trends
        if htf_trend == "neutral" or htf_strength < 15:
            return confidence
        
        adjustment = 0
        
        # Strong trend alignment (strength >= 40)
        if htf_strength >= 40:
            if htf_trend == "bullish" and signal == "buy":
                adjustment = min(25, htf_strength / 2)
            elif htf_trend == "bearish" and signal == "sell":
                adjustment = min(25, htf_strength / 2)
            elif (htf_trend == "bullish" and signal == "sell") or (htf_trend == "bearish" and signal == "buy"):
                adjustment = -min(20, htf_strength / 3)
        
        # Moderate trend alignment (strength 15-39)
        elif htf_strength >= 15:
            if htf_trend == "bullish" and signal == "buy":
                adjustment = min(15, htf_strength / 3)
            elif htf_trend == "bearish" and signal == "sell":
                adjustment = min(15, htf_strength / 3)
            # No penalty for counter-trend in moderate trends
        
        new_confidence = confidence + adjustment
        
        if adjustment > 0:
            logger.info(f"HTF alignment: +{adjustment:.0f}% (HTF: {htf_trend} {htf_strength}%)")
        elif adjustment < 0:
            logger.info(f"HTF contradiction: {adjustment:.0f}% (HTF: {htf_trend} {htf_strength}%)")
        
        return int(max(10, min(95, new_confidence)))

    def is_near_htf_level(self, price: float, tolerance: float = 0.02) -> Dict[str, Any]:
        """Check if price is near HTF support/resistance."""
        if not self.htf_trend:
            return {"near_level": False, "level_type": None}
        
        support = self.htf_trend.get("support")
        resistance = self.htf_trend.get("resistance")
        
        if support and price <= support * (1 + tolerance):
            return {"near_level": True, "level_type": "support", "level_price": support}
        
        if resistance and price >= resistance * (1 - tolerance):
            return {"near_level": True, "level_type": "resistance", "level_price": resistance}
        
        return {"near_level": False, "level_type": None}

    def validate_indicators(self, indicators: Dict[str, Any]) -> bool:
        """Validate that all required indicators are present and valid."""
        required = ['rsi', 'adx', 'sma_fast', 'sma_slow']
        for req in required:
            if req not in indicators or indicators[req] is None:
                logger.warning(f"Missing indicator: {req}")
                return False
            
            # Check for NaN values
            if isinstance(indicators[req], float) and (np.isnan(indicators[req]) or np.isinf(indicators[req])):
                logger.warning(f"Invalid indicator value: {req} = {indicators[req]}")
                return False
                
        return True

    def calculate_base_confidence(self, rsi: float, signal: str) -> int:
        """Calculate base confidence without negative values."""
        if signal == "buy":
            # RSI < 30: confidence increases as RSI decreases
            if rsi < 30:
                return max(40, int(70 - rsi))  # 40-70% range
            else:
                return 0
                
        elif signal == "sell":
            # RSI > 70: confidence increases as RSI increases
            if rsi > 70:
                return max(40, int(rsi - 30))  # 40-70% range
            else:
                return 0
                
        return 0

    @abstractmethod
    def analyze_market(self, candles: List[Dict[str, Any]], price: float, 
                      indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market conditions and return trading signal."""
        pass

    def execute_trade(self, signal: Dict[str, Any], price: float) -> Optional[Dict[str, Any]]:
        """Enhanced trade execution with HTF validation."""
        if signal.get("signal") in ["buy", "sell"] and signal.get("confidence", 0) >= self.min_confidence:
            
            # Additional HTF validation
            htf_validation = self.validate_with_htf(signal["signal"], price)
            if not htf_validation["valid"]:
                logger.warning(f"Trade rejected by HTF validation: {htf_validation['reason']}")
                return None
            
            return {
                "strategy": self.name,
                "type": signal["signal"],
                "entry_price": price,
                "amount": self.calculate_position_size(price, signal["confidence"]),
                "confidence": signal.get("confidence", 0),
                "reason": signal.get("reason", ""),
                "htf_trend": self.htf_trend["trend"] if self.htf_trend else "unknown"
            }
        return None

    def validate_with_htf(self, signal: str, price: float) -> Dict[str, Any]:
        """Validate trade with higher timeframe analysis."""
        if not self.htf_trend:
            return {"valid": True, "reason": "No HTF data"}
        
        htf_level_check = self.is_near_htf_level(price)
        htf_trend = self.htf_trend.get("trend", "neutral")
        htf_strength = self.htf_trend.get("strength", 0)
        
        # Only validate against strong trends
        if htf_strength >= 40:
            # If trading against strong HTF trend, require key level confirmation
            if ((htf_trend == "bullish" and signal == "sell") or
                (htf_trend == "bearish" and signal == "buy")):
                
                if not htf_level_check["near_level"]:
                    return {
                        "valid": False, 
                        "reason": f"Counter-trend trade not near HTF level (HTF: {htf_trend} {htf_strength}%)"
                    }
        
        return {"valid": True, "reason": "HTF validation passed"}

    def calculate_position_size(self, price: float, confidence: int) -> float:
        """Enhanced position sizing with confidence scaling."""
        base_risk = self.config.get('risk_per_trade', 0.02)
        
        # Scale risk based on confidence
        confidence_multiplier = confidence / 100.0
        adjusted_risk = base_risk * confidence_multiplier
        
        # Reduce risk for counter-trend trades
        if self.htf_trend:
            current_signal = "buy" if confidence > 0 else "sell"
            htf_trend = self.htf_trend.get("trend", "neutral")
            htf_strength = self.htf_trend.get("strength", 0)
            
            # Only reduce for strong counter-trend trades
            if htf_strength >= 40:
                if ((htf_trend == "bullish" and current_signal == "sell") or
                    (htf_trend == "bearish" and current_signal == "buy")):
                    adjusted_risk *= 0.5  # 50% risk for counter-trend
        
        risk_amount = self.capital * adjusted_risk
        position_size = risk_amount / price
        
        logger.debug(f"Position size: {position_size:.4f} (confidence: {confidence}%, risk: {adjusted_risk:.3f}%)")
        return round(position_size, 8)  # Round to 8 decimal places for crypto

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information and status."""
        return {
            "name": self.name,
            "min_confidence": self.min_confidence,
            "capital": self.capital,
            "htf_trend": self.htf_trend,
            "config": self.config
        }