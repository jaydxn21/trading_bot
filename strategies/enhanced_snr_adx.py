# strategies/enhanced_snr_adx.py
import logging
import numpy as np
from typing import List, Dict, Any
from .base_strategies import BaseStrategy

logger = logging.getLogger(__name__)

class Enhanced_SNR_ADX_Strategy(BaseStrategy):
    """Enhanced Support & Resistance strategy with HTF integration and extreme condition handling."""

    def __init__(self, config: Dict[str, Any], trading_logic=None):
        super().__init__("Enhanced_SNR_ADX", config)
        self.trading_logic = trading_logic
        self.min_confidence = config.get("min_confidence", 45)  # Lowered to allow more signals
        self.sr_tolerance = config.get("sr_tolerance", 0.005)

    def analyze_market(self, candles: List[Dict[str, Any]], price: float, indicators: Dict[str, Any]) -> Dict[str, Any]:
        if len(candles) < 20:
            return {"signal": "hold", "price": price, "confidence": 0, "reason": "Insufficient data"}
        
        # Validate indicators
        if not self.validate_indicators(indicators):
            return {"signal": "hold", "price": price, "confidence": 0, "reason": "Invalid indicators"}
        
        adx = indicators.get("adx", 0)
        rsi = indicators.get("rsi", 50)
        support = indicators.get("support")
        resistance = indicators.get("resistance")
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        sma_fast = indicators.get("sma_fast")
        sma_slow = indicators.get("sma_slow")
        
        confidence = 0
        signal = "hold"
        reason = "No clear signal"
        
        logger.info(f"[ENHANCED SNR_ADX] Price: {price:.2f}, ADX: {adx:.1f}, RSI: {rsi:.1f}")
        
        # IMPROVED: Better market regime detection for low ADX
        is_weak_trend = adx < 15  # Very weak trend
        is_ranging = adx < 25     # Ranging market
        is_trending = adx >= 25   # Trending market
        
        # 🚨 EXTREME RSI CONDITIONS (override everything)
        if rsi > 80:
            logger.warning(f"🚨 SNR_ADX: Extreme overbought RSI {rsi:.1f}")
            confidence = 55 + min(20, (rsi - 80))
            signal = "sell"
            reason = f"Extreme overbought RSI: {rsi:.1f}"
            
        elif rsi < 20:
            logger.warning(f"🚨 SNR_ADX: Extreme oversold RSI {rsi:.1f}")
            confidence = 55 + min(20, (20 - rsi))
            signal = "buy"
            reason = f"Extreme oversold RSI: {rsi:.1f}"
        
        # NORMAL MARKET CONDITIONS
        elif signal == "hold":
            # VERY WEAK TREND MARKET (ADX < 15) - Focus on strong S/R levels
            if is_weak_trend:
                logger.info(f"[ENHANCED SNR_ADX] Very weak trend market (ADX: {adx:.1f})")
                
                # Strong buy signal: Support + Oversold RSI
                if support and price <= support * (1 + self.sr_tolerance) and rsi < 35:
                    confidence = 52
                    signal = "buy"
                    reason = "Strong buy: Support bounce with oversold RSI in weak trend"
                    
                # Strong sell signal: Resistance + Overbought RSI  
                elif resistance and price >= resistance * (1 - self.sr_tolerance) and rsi > 65:
                    confidence = 52
                    signal = "sell"
                    reason = "Strong sell: Resistance rejection with overbought RSI in weak trend"
                    
                # Moderate signals
                elif support and price <= support * (1 + self.sr_tolerance) and rsi < 50:
                    confidence = 48
                    signal = "buy"
                    reason = "Moderate buy: Support bounce in weak trend"
                    
                elif resistance and price >= resistance * (1 - self.sr_tolerance) and rsi > 50:
                    confidence = 48
                    signal = "sell"
                    reason = "Moderate sell: Resistance rejection in weak trend"
            
            # RANGING MARKET (ADX 15-25)
            elif is_ranging:
                logger.info(f"[ENHANCED SNR_ADX] Ranging market (ADX: {adx:.1f})")
                
                # Buy near support with RSI confirmation
                if support and price <= support * (1 + self.sr_tolerance):
                    base_confidence = 50  # Boosted from 45
                    
                    if rsi < 35:
                        base_confidence += 15
                        reason = "Strong buy: Support bounce with oversold RSI"
                    elif rsi < 50:
                        base_confidence += 10
                        reason = "Buy: Support bounce with favorable RSI"
                    elif rsi < 60:
                        base_confidence += 5
                        reason = "Moderate buy: Support bounce, RSI neutral"
                    else:
                        base_confidence = 0
                        
                    if base_confidence > 0:
                        confidence = min(70, base_confidence)
                        signal = "buy"
                        
                # Sell near resistance with RSI confirmation
                elif resistance and price >= resistance * (1 - self.sr_tolerance):
                    base_confidence = 50  # Boosted from 45
                    
                    if rsi > 65:
                        base_confidence += 15
                        reason = "Strong sell: Resistance rejection with overbought RSI"
                    elif rsi > 50:
                        base_confidence += 10
                        reason = "Sell: Resistance rejection with favorable RSI"
                    elif rsi > 40:
                        base_confidence += 5
                        reason = "Moderate sell: Resistance rejection, RSI neutral"
                    else:
                        base_confidence = 0
                        
                    if base_confidence > 0:
                        confidence = min(70, base_confidence)
                        signal = "sell"
            
            # TRENDING MARKET (ADX >= 25)
            else:
                logger.info(f"[ENHANCED SNR_ADX] Trending market (ADX: {adx:.1f})")
                
                if sma_fast and sma_slow:
                    # UPTREND - Buy pullbacks, avoid selling
                    if sma_fast > sma_slow:
                        if support and price <= support * (1 + self.sr_tolerance) and rsi < 60:
                            confidence = 55 + min(15, (60 - rsi))
                            signal = "buy"
                            reason = "Trend-following buy: Pullback in uptrend"
                        # No sell signals in strong uptrends
                        
                    # DOWNTREND - Sell bounces, avoid buying
                    else:
                        if resistance and price >= resistance * (1 - self.sr_tolerance) and rsi > 40:
                            confidence = 55 + min(15, (rsi - 40))
                            signal = "sell"
                            reason = "Trend-following sell: Bounce in downtrend"
                        # No buy signals in strong downtrends
        
        # Apply HTF trend adjustment for all signals
        if signal != "hold":
            original_confidence = confidence
            confidence = self.adjust_confidence_with_htf(signal, confidence, price)
            
            # Ensure confidence meets minimum threshold
            if confidence < self.min_confidence:
                logger.info(f"[ENHANCED SNR_ADX] Signal rejected: Confidence {confidence}% < {self.min_confidence}% minimum")
                signal = "hold"
                confidence = 0
            else:
                logger.info(f"[ENHANCED SNR_ADX] {signal.upper()} at {price:.2f} - "
                        f"Confidence: {original_confidence}% → {confidence}% - {reason}")
        else:
            logger.info(f"[ENHANCED SNR_ADX] No trade signal - {reason}")
        
        return {
            "signal": signal, 
            "price": price, 
            "confidence": int(confidence), 
            "reason": reason,
            "strategy": "enhanced_snr_adx"
        }

# Add this alias for compatibility  
SNR_ADX_Strategy = Enhanced_SNR_ADX_Strategy