# trading_logic.py - Enhanced with proper config imports

import time
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# Import configuration
try:
    from config import (
        TRADING_ENABLED, INITIAL_BALANCE, RISK_PER_TRADE,
        STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT, MAX_CONSECUTIVE_LOSSES,
        MAX_DAILY_LOSS, MAX_RISK_PERCENT, MIN_CONFIDENCE
    )
    CONFIG_LOADED = True
except ImportError as e:
    print(f"⚠️  Could not import config: {e}")
    # Fallback defaults if config can't be imported
    TRADING_ENABLED = False
    INITIAL_BALANCE = 10000
    RISK_PER_TRADE = 0.02
    STOP_LOSS_PERCENT = 2.0
    TAKE_PROFIT_PERCENT = 4.0
    MAX_CONSECUTIVE_LOSSES = 3
    MAX_DAILY_LOSS = 200
    MAX_RISK_PERCENT = 0.1
    MIN_CONFIDENCE = 50
    CONFIG_LOADED = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests module not available. Real trading will be simulated.")

class TradingLogic:
    def __init__(self, initial_balance: float = INITIAL_BALANCE, risk_per_trade: float = RISK_PER_TRADE):
        if not CONFIG_LOADED:
            logger.warning("⚠️  Using fallback configuration - config.py not loaded properly")
        
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.positions: List[Dict] = []
        self.trade_history: List[Dict] = []
        self.demo_mode = True
        self.equity = initial_balance
        self.consecutive_losses = 0
        self.win_loss_history: List[bool] = []
        self.daily_stats = {
            "start_balance": initial_balance,
            "trades_today": 0,
            "losses_today": 0,
            "daily_pnl": 0,
            "last_reset": datetime.now()
        }
        self.trading_halted = False
        self.halt_reason = ""
    
    def should_stop_trading(self) -> Tuple[bool, str]:
        """Emergency stop conditions"""
        # Check daily loss limit
        daily_loss = self.daily_stats["start_balance"] - self.balance
        if daily_loss > MAX_DAILY_LOSS:
            return True, f"Daily loss limit exceeded: ${daily_loss:.2f}"
        
        # Check consecutive losses
        if self.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
            return True, f"Consecutive losses: {self.consecutive_losses}"
        
        # Check if trading is manually disabled
        if not TRADING_ENABLED:
            return True, "Trading manually disabled"
        
        # Check if already halted
        if self.trading_halted:
            return True, self.halt_reason
            
        return False, ""

    def analyze_market(self, candles: List[Dict], current_price: float) -> Dict[str, Any]:
        """Base market analysis - to be overridden by specific strategies"""
        try:
            if len(candles) < 20:
                return {"signal": "wait", "reason": "Insufficient data", "confidence": 0}
            
            recent_candles = candles[-20:]
            closes = [float(c['close']) for c in recent_candles]
            
            sma_short = sum(closes[-5:]) / 5 if len(closes) >= 5 else closes[-1]
            sma_long = sum(closes) / len(closes) if closes else closes[-1]
            
            trend = "bullish" if sma_short > sma_long else "bearish" if sma_short < sma_long else "neutral"
            
            return {
                "signal": "wait", 
                "trend": trend, 
                "sma_short": sma_short, 
                "sma_long": sma_long,
                "confidence": 0
            }
        except Exception as e:
            logger.error(f"Error in market analysis: {e}")
            return {"signal": "wait", "reason": f"Analysis error: {e}", "confidence": 0}
    
    def execute_trade(self, signal: Dict, current_price: float) -> Optional[Dict]:
        """
        Execute trade with enhanced risk management and emergency stops
        """
        # Check emergency stop conditions
        stop, reason = self.should_stop_trading()
        if stop:
            logger.warning(f"⛔ TRADING HALTED: {reason}")
            self.trading_halted = True
            self.halt_reason = reason
            return None
        
        if signal.get("confidence", 0) < MIN_CONFIDENCE:
            logger.info(f"❌ Trade rejected: Confidence {signal['confidence']}% < {MIN_CONFIDENCE}% threshold")
            return None
        
        if self.demo_mode:
            return self._execute_demo_trade(signal, current_price)
        else:
            return self._execute_real_trade(signal, current_price)
    
    def _execute_demo_trade(self, signal: Dict, current_price: float) -> Optional[Dict]:
        """Execute demo trade with improved risk management"""
        try:
            # Calculate position size with risk management
            position_size = self.calculate_position_size(current_price, signal.get("confidence", 0))
            risk_amount = position_size * current_price
            
            if risk_amount > self.balance * 0.9:  # Leave 10% buffer
                logger.warning("❌ Insufficient balance for trade")
                return None
                
            trade = {
                "id": f"demo_{int(time.time())}_{len(self.positions)}",
                "direction": signal["signal"],
                "entry_price": current_price,
                "size": position_size,
                "amount": risk_amount,
                "timestamp": time.time(),
                "signal_reason": signal.get("reason", ""),
                "confidence": signal.get("confidence", 0),
                "status": "open",
                "demo": True,
                "stop_loss": current_price * (1 - STOP_LOSS_PERCENT/100 if signal["signal"] == "buy" else 1 + STOP_LOSS_PERCENT/100),
                "take_profit": current_price * (1 + TAKE_PROFIT_PERCENT/100 if signal["signal"] == "buy" else 1 - TAKE_PROFIT_PERCENT/100)
            }
            
            self.positions.append(trade)
            self.balance -= risk_amount
            self.daily_stats["trades_today"] += 1
            self._update_equity(current_price)
            
            logger.info(f"📋 TRADE EXECUTED: {trade['direction'].upper()} ${trade['amount']:.2f} at {trade['entry_price']:.5f}")
            logger.info(f"   Confidence: {signal.get('confidence', 0):.1f}%")
            logger.info(f"   New Balance: ${self.balance:.2f}, Open Positions: {len(self.positions)}")
            return trade
            
        except Exception as e:
            logger.error(f"Error executing demo trade: {e}")
            return None
    
    def calculate_position_size(self, current_price: float, confidence: float) -> float:
        """Calculate position size with risk management"""
        base_risk = self.balance * self.risk_per_trade
        
        # Reduce size after losses
        if self.consecutive_losses > 0:
            risk_reduction = 0.5 ** min(3, self.consecutive_losses)
            base_risk *= risk_reduction
            logger.info(f"⚠️  Risk reduction: {risk_reduction:.2f}x due to {self.consecutive_losses} losses")
        
        # Adjust based on confidence
        confidence_factor = max(0.5, confidence / 100.0)  # Minimum 50% of normal size
        base_risk *= confidence_factor
        
        # Hard cap at MAX_RISK_PERCENT of balance
        max_risk = self.balance * MAX_RISK_PERCENT
        final_risk = min(base_risk, max_risk)
        
        return final_risk / current_price

    def _execute_real_trade(self, signal: Dict, current_price: float) -> Optional[Dict]:
        """Execute real trade through Deriv API"""
        try:
            if not REQUESTS_AVAILABLE:
                logger.warning("❌ requests module not available. Cannot execute real trades.")
                return self._execute_demo_trade(signal, current_price)
            
            logger.info(f"🚀 ATTEMPTING REAL TRADE: {signal['signal'].upper()} at {current_price}")
            
            # Simulate API call delay
            time.sleep(0.5)
            
            # Simulate successful trade execution
            trade = self._execute_demo_trade(signal, current_price)
            if trade:
                trade["demo"] = False
                trade["id"] = trade["id"].replace("demo_", "real_")
                logger.info("✅ REAL TRADE EXECUTED SUCCESSFULLY (Simulated)")
            
            return trade
            
        except Exception as e:
            logger.error(f"❌ Real trade execution failed: {e}")
            return None
    
    def _update_equity(self, current_price: float) -> float:
        """Update total equity (balance + unrealized P/L)"""
        unrealized_pnl = 0
        for position in self.positions:
            if position['status'] == 'open':
                if position['direction'] == 'buy':
                    unrealized_pnl += (current_price - position['entry_price']) * position['size']
                else:
                    unrealized_pnl += (position['entry_price'] - current_price) * position['size']
        
        self.equity = self.balance + unrealized_pnl
        self.daily_stats["daily_pnl"] = self.initial_balance - self.balance  # Total loss from start
        return self.equity
    
    def toggle_demo_mode(self) -> bool:
        """Switch between demo and real trading"""
        if not REQUESTS_AVAILABLE:
            logger.warning("⚠️  Real trading requires 'requests' module. Staying in demo mode.")
            return True
            
        self.demo_mode = not self.demo_mode
        mode = "DEMO" if self.demo_mode else "REAL"
        logger.info(f"🔁 Trading mode switched to: {mode}")
        
        if not self.demo_mode:
            logger.info("💡 Note: Real trading is currently simulated. Add your Deriv API credentials to enable actual trading.")
            
        return self.demo_mode
    
    def set_risk_level(self, risk_level: float) -> bool:
        """Set risk per trade percentage"""
        if 0 < risk_level <= MAX_RISK_PERCENT:
            self.risk_per_trade = risk_level
            logger.info(f"🎯 Risk level set to: {risk_level * 100}%")
            return True
        logger.warning(f"❌ Invalid risk level: {risk_level}. Max allowed: {MAX_RISK_PERCENT}")
        return False
    
    def manage_open_positions(self, current_price: float) -> List[Dict]:
        """Manage open positions (stop loss, take profit)"""
        closed_positions = []
        
        for position in self.positions[:]:
            if position.get('status') != 'open':
                continue
                
            pnl_pct = self._calculate_pnl_percentage(position, current_price)
            
            # Take profit
            if pnl_pct >= TAKE_PROFIT_PERCENT:
                profit = self.close_position(position['id'], current_price)
                if profit is not None:
                    closed_positions.append({
                        "id": position['id'], 
                        "reason": "Take profit", 
                        "pnl": profit,
                        "pnl_pct": pnl_pct
                    })
            
            # Stop loss
            elif pnl_pct <= -STOP_LOSS_PERCENT:
                loss = self.close_position(position['id'], current_price)
                if loss is not None:
                    closed_positions.append({
                        "id": position['id'], 
                        "reason": "Stop loss", 
                        "pnl": loss,
                        "pnl_pct": pnl_pct
                    })
        
        # Update equity after closing positions
        self._update_equity(current_price)
        return closed_positions
    
    def _calculate_pnl_percentage(self, position: Dict, current_price: float) -> float:
        """Calculate P/L percentage for a position"""
        if position['direction'] == 'buy':
            return (current_price - position["entry_price"]) / position["entry_price"] * 100
        else:
            return (position["entry_price"] - current_price) / position["entry_price"] * 100
    
    def close_position(self, position_id: str, exit_price: float) -> Optional[float]:
        """Close a position and update balance"""
        position = next((p for p in self.positions if p["id"] == position_id), None)
        if not position or position.get('status') != 'open':
            return None
            
        try:
            if position['direction'] == 'buy':
                profit_loss = (exit_price - position["entry_price"]) * position["size"]
            else:
                profit_loss = (position["entry_price"] - exit_price) * position["size"]
            
            position["status"] = "closed"
            position["exit_price"] = exit_price
            position["exit_time"] = time.time()
            position["profit_loss"] = profit_loss
            
            self.positions.remove(position)
            self.trade_history.append(position)
            
            # Update balance with realized P/L
            self.balance += profit_loss
            self._update_equity(exit_price)
            
            logger.info(f"💰 POSITION CLOSED: {position_id} P/L: ${profit_loss:.2f}")
            logger.info(f"   New Balance: ${self.balance:.2f}")
            
            # Track win/loss for risk management
            if profit_loss > 0:
                self.consecutive_losses = 0
                logger.info("✅ WINNING TRADE")
            else:
                self.consecutive_losses += 1
                self.daily_stats["losses_today"] += 1
                logger.info(f"❌ LOSING TRADE ({self.consecutive_losses} consecutive)")
            
            return profit_loss
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None
    
    def close_all_positions(self, current_price: float) -> List[Dict]:
        """Close all open positions"""
        closed = []
        for position in self.positions[:]:
            if position.get('status') == 'open':
                pnl = self.close_position(position['id'], current_price)
                if pnl is not None:
                    closed.append({"id": position['id'], "pnl": pnl})
        return closed
    
    def get_account_summary(self, current_price: float) -> Dict:
        """Get complete account summary with serializable data"""
        self._update_equity(current_price)
        
        summary = {
            "balance": self.balance,
            "equity": self.equity,
            "open_positions": len(self.positions),
            "total_trades": len(self.trade_history),
            "demo_mode": self.demo_mode,
            "risk_level": self.risk_per_trade,
            "consecutive_losses": self.consecutive_losses,
            "trading_halted": self.trading_halted,
            "halt_reason": self.halt_reason,
            "daily_stats": self.daily_stats  # This should already be serializable
        }
        
        return summary
    
    def reset_account(self, new_balance: Optional[float] = None) -> None:
        """Reset account to initial state"""
        self.balance = new_balance if new_balance is not None else self.initial_balance
        self.positions = []
        self.trade_history = []
        self.equity = self.balance
        self.consecutive_losses = 0
        self.win_loss_history = []
        self.trading_halted = False
        self.halt_reason = ""
        self.daily_stats = {
            "start_balance": self.balance,
            "trades_today": 0,
            "losses_today": 0,
            "daily_pnl": 0,
            "last_reset": datetime.now()
        }
        
        logger.info(f"🔄 Account reset to ${self.balance:.2f}")
    
    def analyze_performance(self) -> Dict:
        """Analyze trading performance"""
        if not self.trade_history:
            return {"message": "No trades yet"}
        
        wins = [t for t in self.trade_history if t.get('profit_loss', 0) > 0]
        losses = [t for t in self.trade_history if t.get('profit_loss', 0) <= 0]
        
        total_trades = len(self.trade_history)
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = sum(t['profit_loss'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['profit_loss'] for t in losses) / len(losses) if losses else 0
        profit_factor = abs(avg_win * len(wins) / (avg_loss * len(losses))) if losses and avg_loss != 0 else float('inf')
        
        analysis = {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "wins": len(wins),
            "losses": len(losses),
            "average_win": avg_win,
            "average_loss": avg_loss,
            "profit_factor": profit_factor,
            "consecutive_losses": self.consecutive_losses,
            "total_profit": sum(t['profit_loss'] for t in self.trade_history)
        }
        
        logger.info("=== PERFORMANCE ANALYSIS ===")
        logger.info(f"Total Trades: {total_trades}")
        logger.info(f"Win Rate: {win_rate:.1f}%")
        logger.info(f"Average Win: ${avg_win:.2f}")
        logger.info(f"Average Loss: ${avg_loss:.2f}")
        logger.info(f"Profit Factor: {profit_factor:.2f}")
        
        # Analyze last 5 losses
        if losses:
            logger.info("--- Last 5 Losses ---")
            for loss in losses[-5:]:
                logger.info(f"Loss: ${loss.get('profit_loss', 0):.2f} - {loss.get('signal_reason', 'No reason')}")
        
        return analysis

    def resume_trading(self) -> bool:
        """Resume trading after being halted"""
        if self.trading_halted:
            self.trading_halted = False
            self.halt_reason = ""
            logger.info("✅ Trading resumed")
            return True
        return False