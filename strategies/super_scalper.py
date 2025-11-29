# strategies/super_scalper.py
import numpy as np
from datetime import datetime
import logging
from typing import List, Dict, Any
from .base_strategies import BaseStrategy

logger = logging.getLogger(__name__)

class SuperScalperStrategy(BaseStrategy):
    """High-frequency burst trading optimized for R_100 volatility index"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("super_scalper", config or {})
        self.min_confidence = self.config.get('min_confidence', 70)
        self.last_burst_time = None
        self.burst_interval = 10  # minutes
        self.trades_per_burst = 5
        self.target_profit_percent = 20

    def analyze_market(self, candles: List[Dict[str, Any]], current_price: float, indicators: Dict[str, Any]) -> Dict[str, Any]:
        if len(candles) < 15:
            return {"signal": "hold", "price": current_price, "confidence": 0, "reason": "Insufficient data"}
            
        # Use provided indicators or calculate
        calc_indicators = self._calculate_r100_indicators(candles, current_price)
        indicators = {**calc_indicators, **(indicators or {})}

        if self._should_execute_burst() and self._is_good_burst_condition(indicators):
            signal = self._generate_burst_signal(current_price, indicators)
            if signal and signal.get("signal") != "hold":
                self.last_burst_time = datetime.now()
                logger.info(f"SUPER SCALPER BURST: {signal['signal'].upper()} at {current_price:.2f}")
                return signal
                
        return {"signal": "hold", "price": current_price, "confidence": 0, "reason": "Not in burst mode"}

    def _calculate_r100_indicators(self, candles, current_price):
        """Calculate indicators optimized for R_100 volatility index"""
        closes = np.array([c['close'] for c in candles[-30:]])
        highs = np.array([c['high'] for c in candles[-30:]])
        lows = np.array([c['low'] for c in candles[-30:]])
        
        # Ultra-fast moving averages for R_100
        ma_3 = np.mean(closes[-3:])
        ma_5 = np.mean(closes[-5:])
        ma_8 = np.mean(closes[-8:])
        
        # Momentum indicators (very short-term)
        momentum_3 = ((current_price - closes[-3]) / closes[-3]) * 100
        momentum_5 = ((current_price - closes[-5]) / closes[-5]) * 100
        
        # Volatility measurement for R_100
        recent_volatility = np.std(closes[-10:]) / np.mean(closes[-10:]) * 100
        
        # Price position in recent range
        recent_high = np.max(highs[-10:])
        recent_low = np.min(lows[-10:])
        price_position = (current_price - recent_low) / (recent_high - recent_low) * 100 if recent_high != recent_low else 50
        
        # RSI-like calculation for R_100
        price_changes = np.diff(closes[-14:])
        gains = np.where(price_changes > 0, price_changes, 0)
        losses = np.where(price_changes < 0, -price_changes, 0)
        
        avg_gain = np.mean(gains) if len(gains) > 0 else 0.001
        avg_loss = np.mean(losses) if len(losses) > 0 else 0.001
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return {
            'ma_3': ma_3,
            'ma_5': ma_5,
            'ma_8': ma_8,
            'momentum_3': momentum_3,
            'momentum_5': momentum_5,
            'volatility': recent_volatility,
            'price_position': price_position,
            'rsi': rsi,
            'recent_high': recent_high,
            'recent_low': recent_low
        }
    
    def _should_execute_burst(self):
        """Check if it's time to execute a burst"""
        current_time = datetime.now()
        
        if self.last_burst_time is None:
            return True
            
        time_since_last = (current_time - self.last_burst_time).total_seconds() / 60
        return time_since_last >= self.burst_interval
    
    def _is_good_burst_condition(self, indicators):
        """Check if R_100 market conditions are suitable for burst trading"""
        volatility = indicators['volatility']
        rsi = indicators['rsi']
        momentum = indicators['momentum_5']
        
        # R_100 specific conditions
        if volatility < 0.5:  # Too low volatility for R_100
            logger.debug("SUPER SCALPER: Volatility too low for R_100")
            return False
            
        if volatility > 3.0:  # Too high volatility for R_100
            logger.debug("SUPER SCALPER: Volatility too high for R_100")
            return False
            
        if abs(momentum) > 2.0:  # Too much momentum (overextended)
            logger.debug("SUPER SCALPER: Momentum too extreme")
            return False
            
        # Good RSI range for burst trading
        if rsi < 20 or rsi > 80:  # Avoid extremes
            logger.debug("SUPER SCALPER: RSI at extreme")
            return False
            
        logger.debug("SUPER SCALPER: Good burst conditions met")
        return True
    
    def _generate_burst_signal(self, current_price, indicators):
        """Generate burst trading signal for R_100"""
        ma_3 = indicators['ma_3']
        ma_5 = indicators['ma_5']
        ma_8 = indicators['ma_8']
        momentum_3 = indicators['momentum_3']
        rsi = indicators['rsi']
        price_pos = indicators['price_position']
        
        # Multiple condition scoring for R_100
        buy_score = 0
        sell_score = 0
        
        # Moving average alignment (bullish)
        if ma_3 > ma_5 > ma_8:
            buy_score += 2
        elif ma_3 < ma_5 < ma_8:
            sell_score += 2
        
        # Momentum direction
        if momentum_3 > 0.1:
            buy_score += 1
        elif momentum_3 < -0.1:
            sell_score += 1
            
        # RSI position
        if 30 < rsi < 50:  # Mildly oversold
            buy_score += 1
        elif 50 < rsi < 70:  # Mildly overbought
            sell_score += 1
            
        # Price position in range
        if price_pos < 30:  # Near support
            buy_score += 1
        elif price_pos > 70:  # Near resistance
            sell_score += 1
        
        # Determine signal
        if buy_score >= 3 and buy_score > sell_score:
            return {
                'signal': 'buy',
                'price': current_price,
                'confidence': 75,
                'reason': f"R_100 BURST BUY - MA alignment + momentum",
                'burst_trades': self.trades_per_burst,
                'target_percent': self.target_profit_percent,
                'strategy': 'super_scalper'
            }
        elif sell_score >= 3 and sell_score > buy_score:
            return {
                'signal': 'sell', 
                'price': current_price,
                'confidence': 75,
                'reason': f"R_100 BURST SELL - MA alignment + momentum",
                'burst_trades': self.trades_per_burst,
                'target_percent': self.target_profit_percent,
                'strategy': 'super_scalper'
            }
        
        return None