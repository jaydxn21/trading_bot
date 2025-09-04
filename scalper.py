# scalper.py - Enhanced scalping strategy with proper config imports

from trading_logic import TradingLogic
import numpy as np
import time
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Import configuration
try:
    from config import SCALPER_CONFIG, MIN_CONFIDENCE
    CONFIG_LOADED = True
except ImportError:
    # Fallback defaults
    SCALPER_CONFIG = {
        "rsi_period": 7,
        "bollinger_period": 10,
        "stochastic_period": 14,
        "confidence_threshold": 78,
        "min_volatility": 0.2,
        "required_confirmations": 2
    }
    MIN_CONFIDENCE = 78
    CONFIG_LOADED = False
    logger.warning("⚠️  Using fallback configuration - config.py not loaded properly")

class ScalperStrategy(TradingLogic):
    def __init__(self, initial_balance=10000, risk_per_trade=0.02):
        super().__init__(initial_balance, risk_per_trade)
        self.last_signals = []
        self.last_price = None
        self.win_loss_history = []
        self.consecutive_losses = 0
        self.trade_filters = {
            "min_volatility": SCALPER_CONFIG["min_volatility"],
            "required_confirmations": SCALPER_CONFIG["required_confirmations"],
            "avoid_late_night": True,
            "trend_alignment_required": True
        }
    
    def should_enter_trade(self, signal, current_price):
        """Enhanced trade entry filters"""
        # Check minimum confidence
        if signal.get('confidence', 0) < SCALPER_CONFIG["confidence_threshold"]:
            return False, f"Low confidence ({signal.get('confidence', 0)}%)"
        
        # Check volatility
        if signal.get('volatility', 0) < self.trade_filters["min_volatility"]:
            return False, f"Low volatility ({signal.get('volatility', 0):.2f}%)"
        
        # Avoid late night trading (if enabled)
        if self.trade_filters["avoid_late_night"]:
            current_hour = time.localtime().tm_hour
            if current_hour in [0, 1, 2, 3, 22, 23]:  # 10PM - 4AM
                return False, "Late night trading avoided"
        
        # Check trend alignment
        if self.trade_filters["trend_alignment_required"]:
            short_trend = signal.get('short_trend', 'neutral')
            medium_trend = signal.get('medium_trend', 'neutral')
            if short_trend != medium_trend:
                return False, "Trend misalignment"
        
        # Check if we're in recovery mode after losses
        if self.consecutive_losses > 0 and signal.get('confidence', 0) < 85:
            return False, f"Recovery mode - need higher confidence ({self.consecutive_losses} losses)"
        
        return True, "Trade approved"
    
    def analyze_market(self, candles, current_price):
        """
        Enhanced scalping strategy with confidence scoring
        """
        if len(candles) < 20:
            return {"signal": "wait", "reason": "Insufficient data", "confidence": 0}
        
        # Check emergency stop first
        stop, reason = self.should_stop_trading()
        if stop:
            return {"signal": "wait", "reason": f"Trading halted: {reason}", "confidence": 0}
        
        try:
            # Get recent candles for analysis - extract only price arrays
            recent_candles = candles[-20:]
            closes = [float(c['close']) for c in recent_candles]
            highs = [float(c['high']) for c in recent_candles]
            lows = [float(c['low']) for c in recent_candles]
            
            # Calculate multiple indicators using config values
            rsi = self._calculate_rsi(closes, period=SCALPER_CONFIG["rsi_period"])
            bb_upper, bb_lower, sma = self._calculate_bollinger_bands(closes, 
                                                                     period=SCALPER_CONFIG["bollinger_period"], 
                                                                     num_std=1.5)
            
            # Handle stochastic calculation with error handling
            try:
                stoch_k, stoch_d = self._calculate_stochastic(highs, lows, closes, 
                                                             period=SCALPER_CONFIG["stochastic_period"])
            except Exception as e:
                logger.warning(f"⚠️  Stochastic calculation failed: {e}")
                stoch_k, stoch_d = 50, 50  # Default values
            
            atr = self._calculate_atr(highs, lows, closes)
            
            # Price action analysis
            price_change = current_price - closes[-2] if len(closes) >= 2 else 0
            price_change_pct = (price_change / closes[-2] * 100) if len(closes) >= 2 and closes[-2] != 0 else 0
            volatility = atr / current_price * 100  # Volatility as percentage
            
            # Trend analysis
            short_trend = self._calculate_trend(closes[-5:]) if len(closes) >= 5 else "neutral"
            medium_trend = self._calculate_trend(closes[-10:]) if len(closes) >= 10 else "neutral"
            
            # Confidence scoring system (0-100%)
            confidence = 0
            signal_reasons = []
            buy_strength = 0
            sell_strength = 0
            
            # 1. Bollinger Band signals (25% weight)
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) * 100 if bb_upper != bb_lower else 50
            
            if bb_position < 20:  # Oversold
                confidence += 25
                buy_strength += (20 - bb_position) * 1.2
                signal_reasons.append("BB oversold")
            elif bb_position > 80:  # Overbought
                confidence += 25
                sell_strength += (bb_position - 80) * 1.2
                signal_reasons.append("BB overbought")
            
            # 2. RSI signals (25% weight)
            if rsi < 30:  # Oversold
                confidence += 25
                buy_strength += (30 - rsi) * 1.5
                signal_reasons.append("RSI oversold")
            elif rsi > 70:  # Overbought
                confidence += 25
                sell_strength += (rsi - 70) * 1.5
                signal_reasons.append("RSI overbought")
            
            # 3. Stochastic signals (20% weight)
            if stoch_k < 25 and stoch_d < 25:
                confidence += 20
                buy_strength += 40
                signal_reasons.append("Stochastic oversold")
            elif stoch_k > 75 and stoch_d > 75:
                confidence += 20
                sell_strength += 40
                signal_reasons.append("Stochastic overbought")
            
            # 4. Trend alignment (15% weight)
            if short_trend == medium_trend:
                confidence += 15
                if short_trend == "bullish":
                    buy_strength += 20
                elif short_trend == "bearish":
                    sell_strength += 20
                signal_reasons.append("Trend aligned")
            
            # 5. Momentum confirmation (15% weight)
            if (bb_position < 30 and price_change_pct > 0.1) or (bb_position > 70 and price_change_pct < -0.1):
                confidence += 15
                signal_reasons.append("Momentum confirmation")
            
            # Adjust confidence based on recent performance
            confidence = self._adjust_confidence(confidence)
            
            # Determine signal direction
            if buy_strength > sell_strength and buy_strength > 60:
                signal = "buy"
            elif sell_strength > buy_strength and sell_strength > 60:
                signal = "sell"
            else:
                signal = "wait"
                signal_reasons.append("No clear signal strength")
            
            # Apply trade filters
            if signal != "wait":
                should_enter, filter_reason = self.should_enter_trade({
                    "confidence": confidence,
                    "volatility": volatility,
                    "short_trend": short_trend,
                    "medium_trend": medium_trend
                }, current_price)
                
                if not should_enter:
                    signal = "wait"
                    signal_reasons.append(filter_reason)
            
            # Apply confidence filter
            if confidence < SCALPER_CONFIG["confidence_threshold"]:
                signal = "wait"
                signal_reasons.append(f"Low confidence ({confidence:.1f}% < {SCALPER_CONFIG['confidence_threshold']}%)")
            
            # Use current time
            current_timestamp = int(time.time())
            
            analysis = {
                "signal": signal,
                "reason": " | ".join(signal_reasons[:3]),  # Show top 3 reasons
                "confidence": confidence,
                "rsi": rsi,
                "bb_upper": bb_upper,
                "bb_lower": bb_lower,
                "bb_middle": sma,
                "bb_position": bb_position,
                "stoch_k": stoch_k,
                "stoch_d": stoch_d,
                "volatility": volatility,
                "price_change_pct": price_change_pct,
                "current_price": current_price,
                "short_trend": short_trend,
                "medium_trend": medium_trend,
                "timestamp": current_timestamp,
                "buy_strength": buy_strength,
                "sell_strength": sell_strength
            }
            
            logger.info(f"\n=== ENHANCED SCALPER ANALYSIS ===")
            logger.info(f"Price: {current_price:.5f}, RSI: {rsi:.1f}, Confidence: {confidence:.1f}%")
            logger.info(f"Bollinger: {bb_lower:.5f}-{bb_upper:.5f} (Position: {bb_position:.1f}%)")
            logger.info(f"Stochastic: K={stoch_k:.1f}, D={stoch_d:.1f}, Volatility: {volatility:.2f}%")
            logger.info(f"Signal: {signal.upper()} - {analysis['reason']}")
            logger.info(f"Buy Strength: {buy_strength:.1f}, Sell Strength: {sell_strength:.1f}")
            logger.info("=" * 60)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in market analysis: {e}")
            return {"signal": "wait", "reason": f"Analysis error: {e}", "confidence": 0}
    
    def _adjust_confidence(self, base_confidence):
        """Adjust confidence based on recent performance"""
        # Reduce confidence after consecutive losses
        if self.consecutive_losses > 0:
            confidence_reduction = min(25, self.consecutive_losses * 8)
            adjusted_confidence = max(0, base_confidence - confidence_reduction)
            logger.info(f"   Confidence reduced by {confidence_reduction}% due to {self.consecutive_losses} consecutive losses")
            return adjusted_confidence
        return base_confidence
    
    def execute_trade(self, signal, current_price):
        """Override to apply confidence filter"""
        if signal.get("confidence", 0) < SCALPER_CONFIG["confidence_threshold"]:
            logger.info(f"❌ Trade rejected: Confidence {signal.get('confidence', 0):.1f}% < {SCALPER_CONFIG['confidence_threshold']}% threshold")
            return None
        
        return super().execute_trade(signal, current_price)
    
    def close_position(self, position_id, exit_price):
        """Track win/loss history for confidence adjustment"""
        profit_loss = super().close_position(position_id, exit_price)
        
        if profit_loss is not None:
            if profit_loss > 0:
                self.consecutive_losses = 0
                self.win_loss_history.append(True)
                logger.info("✅ WINNING TRADE")
            else:
                self.consecutive_losses += 1
                self.win_loss_history.append(False)
                logger.info(f"❌ LOSING TRADE ({self.consecutive_losses} consecutive)")
            
            # Keep only last 20 trades
            if len(self.win_loss_history) > 20:
                self.win_loss_history.pop(0)
        
        return profit_loss
    
    def _calculate_rsi(self, prices, period=7):
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:]) if len(gains) >= period else 0
        avg_loss = np.mean(losses[-period:]) if len(losses) >= period else 0.001
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return max(0, min(100, rsi))
    
    def _calculate_bollinger_bands(self, prices, period=10, num_std=1.5):
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            sma = prices[-1] if prices else 0
            return sma * 1.02, sma * 0.98, sma
        
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        
        return upper_band, lower_band, sma
    
    def _calculate_stochastic(self, highs, lows, closes, period=14, k_smooth=3, d_smooth=3):
        """Calculate Stochastic oscillator with proper error handling"""
        try:
            if len(highs) < period or len(lows) < period or len(closes) < period:
                return 50, 50
            
            # Calculate %K values
            k_values = []
            for i in range(period, len(closes)):
                period_highs = highs[i-period:i]
                period_lows = lows[i-period:i]
                
                if not period_highs or not period_lows:
                    continue
                    
                highest_high = max(period_highs)
                lowest_low = min(period_lows)
                
                if highest_high == lowest_low:
                    k_values.append(50)
                else:
                    k = 100 * (closes[i] - lowest_low) / (highest_high - lowest_low)
                    k_values.append(k)
            
            # If no K values calculated, return defaults
            if not k_values:
                return 50, 50
            
            # Smooth %K (fast stochastic)
            if len(k_values) >= k_smooth:
                stoch_k = sum(k_values[-k_smooth:]) / k_smooth
            else:
                stoch_k = sum(k_values) / len(k_values)
            
            # Calculate %D (slow stochastic) - SMA of %K
            if len(k_values) >= d_smooth:
                stoch_d = sum(k_values[-d_smooth:]) / d_smooth
            else:
                stoch_d = sum(k_values) / len(k_values)
            
            return stoch_k, stoch_d
            
        except Exception as e:
            logger.error(f"❌ Stochastic calculation error: {e}")
            return 50, 50  # Return neutral values on error
    
    def _calculate_atr(self, highs, lows, closes, period=14):
        """Calculate Average True Range"""
        if len(highs) < period or len(lows) < period or len(closes) < period:
            return 0
        
        tr_values = []
        for i in range(1, len(highs)):
            high = highs[i]
            low = lows[i]
            prev_close = closes[i-1]
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            tr = max(tr1, tr2, tr3)
            tr_values.append(tr)
        
        return np.mean(tr_values[-period:]) if tr_values else 0
    
    def _calculate_trend(self, prices):
        """Calculate trend direction"""
        if len(prices) < 2:
            return "neutral"
        
        price_change = prices[-1] - prices[0]
        if price_change > 0.001:  # Small buffer to avoid noise
            return "bullish"
        elif price_change < -0.001:
            return "bearish"
        else:
            return "neutral"