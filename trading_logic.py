# trading_logic.py - COMPLETE FIXED VERSION
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import config

logger = logging.getLogger(__name__)

class TradingLogic:
    def __init__(self, starting_balance: float = 10000.0, risk_per_trade: float = 0.02):
        self.balance = starting_balance
        self.initial_balance = starting_balance
        self.risk_per_trade = risk_per_trade
        self.positions: List[Dict[str, Any]] = []
        self.closed_positions: List[Dict[str, Any]] = []
        self.position_id_counter = 0
        self.current_price = 0.0
        
        # Enhanced performance tracking - FIXED: Initialize properly
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'win_rate': 0.0
        }
        
        # Enhanced risk management
        self.daily_stats = {
            "date": datetime.now().date(),
            "trades_today": 0,
            "pnl_today": 0.0,
            "winning_trades": 0,
            "losing_trades": 0
        }
        
        self.strategy_stats = {}
        self.consecutive_losses = 0
        self.max_consecutive_losses = getattr(config, 'MAX_CONSECUTIVE_LOSSES', 3)
        self.win_streak = 0
        self.daily_loss_limit = getattr(config, 'MAX_DAILY_LOSS', 200)
        self.daily_losses = 0.0
        
        # Strategy cooldown tracking
        self.strategy_cooldowns = {}
        self.min_cooldown_minutes = 3

    def generate_position_id(self):
        """Generate unique position ID"""
        self.position_id_counter += 1
        return f"pos_{self.position_id_counter}_{int(datetime.now().timestamp())}"

    def update_price(self, current_price: float):
        """Update current price and calculate floating P&L for all positions"""
        self.current_price = current_price
        
        for position in self.positions:
            if position.get('status') == 'open':
                # Calculate current P&L
                if position['direction'] == 'buy':
                    current_pnl = (current_price - position['entry_price']) * position['size']
                else:
                    current_pnl = (position['entry_price'] - current_price) * position['size']
                
                position['current_price'] = current_price
                position['current_pnl'] = current_pnl - position.get('trade_cost', 0)
                position['floating_profit'] = position['current_pnl']

    def calculate_position_size(self, stop_distance: float, price: float, confidence: float = 50, strategy: str = "default") -> float:
        """Calculate position size with risk management"""
        if stop_distance <= 0:
            return 0
        
        # Base risk calculation
        base_risk = self.risk_per_trade
        
        # Confidence-based adjustment
        confidence_multiplier = 0.5 + (confidence / 100.0)
        
        # Strategy-specific risk adjustment
        strategy_multiplier = self.get_strategy_risk_multiplier(strategy)
        
        # Consecutive losses protection
        if self.consecutive_losses >= 1:
            loss_multiplier = max(0.1, 1.0 - (self.consecutive_losses * 0.3))
            base_risk *= loss_multiplier
        
        # Daily loss limit protection
        daily_loss_ratio = abs(self.daily_losses) / self.daily_loss_limit
        if daily_loss_ratio > 0.5:
            limit_multiplier = max(0.1, 1.0 - daily_loss_ratio)
            base_risk *= limit_multiplier
        
        # Calculate final risk amount
        risk_amount = self.balance * base_risk * confidence_multiplier * strategy_multiplier
        size = risk_amount / stop_distance
        
        # Position size limits
        max_size = (self.balance * 0.05) / price
        min_size = (self.balance * 0.005) / price
        size = max(min(size, max_size), min_size)
        
        return round(size, 6)

    def get_strategy_risk_multiplier(self, strategy: str) -> float:
        """Get risk multiplier based on strategy performance"""
        if strategy not in self.strategy_stats:
            return 1.0
        
        stats = self.strategy_stats[strategy]
        total_trades = stats.get("total_trades", 0)
        winning_trades = stats.get("winning_trades", 0)
        
        if total_trades < 5:
            return 1.0
        
        win_rate = winning_trades / total_trades
        
        if win_rate > 0.6:
            return 1.2
        elif win_rate < 0.4:
            return 0.7
        else:
            return 1.0

    def open_position(self, direction: str, entry_price: float, stop_loss: float, 
                     take_profit: float, strategy: str, trade_cost: float = 0.001,
                     confidence: float = 50, volatility: float = 0.002) -> Optional[str]:
        """Open a new position with proper validation"""
        try:
            # Calculate position size based on risk
            if direction == "buy":
                risk_per_unit = entry_price - stop_loss
            else:  # sell
                risk_per_unit = stop_loss - entry_price
                
            if risk_per_unit <= 0:
                logger.error("❌ Invalid risk calculation - stop loss too close to entry")
                return None
                
            position_size = self.calculate_position_size(risk_per_unit, entry_price, confidence, strategy)
            
            # Ensure minimum position size
            if position_size * entry_price < 1:  # Minimum $1 position
                position_size = 1 / entry_price
                
            position_id = self.generate_position_id()
            
            position = {
                'id': position_id,
                'direction': direction,
                'entry_price': float(entry_price),
                'current_price': float(entry_price),
                'stop_loss': float(stop_loss),
                'take_profit': float(take_profit),
                'size': float(position_size),
                'strategy': strategy,
                'confidence': float(confidence),
                'opened_at': datetime.now(),
                'closed_at': None,
                'status': 'open',
                'pnl': 0.0,
                'floating_profit': 0.0,
                'trade_cost': float(trade_cost),
                'volatility': float(volatility),
                'close_reason': None
            }
            
            # Deduct trade cost
            cost = position_size * entry_price * trade_cost
            self.balance -= cost
            position['trade_cost_amount'] = cost
            
            self.positions.append(position)
            logger.info(f"📈 OPENED {direction} position: {position_id} @ ${entry_price:.4f}")
            
            return position_id
            
        except Exception as e:
            logger.error(f"❌ Error opening position: {e}")
            return None

    def manage_open_positions(self, current_price: float) -> List[Dict]:
        """Manage open positions - check for stop loss, take profit, and timeouts"""
        self.update_price(current_price)
        closed_positions = []
        
        current_time = datetime.now()
        
        for position in self.positions[:]:  # Use slice copy to avoid modification during iteration
            if position.get('status') != 'open':
                continue
                
            # Check stop loss and take profit
            should_close = False
            close_reason = ""
            pnl = position.get('floating_profit', 0)
            
            if position['direction'] == 'buy':
                if current_price <= position['stop_loss']:
                    should_close = True
                    close_reason = "stop_loss"
                    # Use stop loss price for calculation
                    pnl = (position['stop_loss'] - position['entry_price']) * position['size'] - position.get('trade_cost_amount', 0)
                elif current_price >= position['take_profit']:
                    should_close = True
                    close_reason = "take_profit"
                    # Use take profit price for calculation
                    pnl = (position['take_profit'] - position['entry_price']) * position['size'] - position.get('trade_cost_amount', 0)
            else:  # sell
                if current_price >= position['stop_loss']:
                    should_close = True
                    close_reason = "stop_loss"
                    pnl = (position['entry_price'] - position['stop_loss']) * position['size'] - position.get('trade_cost_amount', 0)
                elif current_price <= position['take_profit']:
                    should_close = True
                    close_reason = "take_profit"
                    pnl = (position['entry_price'] - position['take_profit']) * position['size'] - position.get('trade_cost_amount', 0)
            
            # Check timeout (8 minutes)
            time_open = (current_time - position['opened_at']).total_seconds()
            if time_open >= 480:  # 8 minutes
                should_close = True
                close_reason = "timeout"
                # Use current price for timeout close
                if position['direction'] == 'buy':
                    pnl = (current_price - position['entry_price']) * position['size'] - position.get('trade_cost_amount', 0)
                else:
                    pnl = (position['entry_price'] - current_price) * position['size'] - position.get('trade_cost_amount', 0)
            
            if should_close:
                # Close the position
                position['status'] = 'closed'
                position['closed_at'] = current_time
                position['pnl'] = pnl
                position['close_reason'] = close_reason
                position['exit_price'] = current_price
                
                # Update balance
                self.balance += pnl
                
                # Move to closed positions
                self.positions.remove(position)
                self.closed_positions.append(position)
                
                # Update performance stats
                self.update_performance_stats(position)
                
                closed_positions.append({
                    'id': position['id'],
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'size': position['size'],
                    'strategy': position['strategy'],
                    'pnl': pnl,
                    'reason': close_reason,
                    'timestamp': current_time
                })
                
                logger.info(f"📉 CLOSED {position['direction']} position: {position['id']} "
                           f"| P&L: ${pnl:.2f} | Reason: {close_reason}")
        
        return closed_positions

    def update_performance_stats(self, closed_position: Dict):
        """Update performance statistics when a position closes"""
        pnl = closed_position.get('pnl', 0)
        
        self.performance_stats['total_trades'] += 1
        self.performance_stats['total_profit'] += pnl
        
        if pnl > 0:
            self.performance_stats['winning_trades'] += 1
            self.consecutive_losses = 0
            self.win_streak += 1
        else:
            self.performance_stats['losing_trades'] += 1
            self.consecutive_losses += 1
            self.win_streak = 0
        
        # Calculate win rate
        if self.performance_stats['total_trades'] > 0:
            self.performance_stats['win_rate'] = (
                self.performance_stats['winning_trades'] / 
                self.performance_stats['total_trades'] * 100
            )
        
        # Update strategy stats
        strategy = closed_position.get('strategy', 'unknown')
        if strategy not in self.strategy_stats:
            self.strategy_stats[strategy] = {
                "total_trades": 0,
                "winning_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0
            }
        
        stats = self.strategy_stats[strategy]
        stats["total_trades"] += 1
        stats["total_pnl"] += pnl
        
        if pnl > 0:
            stats["winning_trades"] += 1
        
        stats["win_rate"] = stats["winning_trades"] / stats["total_trades"] * 100 if stats["total_trades"] > 0 else 0

    def close_all_open_trades(self, current_price: float) -> List[Dict]:
        """Emergency close all open trades at current price"""
        closed_positions = []
        current_time = datetime.now()
        
        for position in self.positions[:]:
            if position.get('status') == 'open':
                # Calculate P&L at current price
                if position['direction'] == 'buy':
                    pnl = (current_price - position['entry_price']) * position['size'] - position.get('trade_cost_amount', 0)
                else:
                    pnl = (position['entry_price'] - current_price) * position['size'] - position.get('trade_cost_amount', 0)
                
                # Close the position
                position['status'] = 'closed'
                position['closed_at'] = current_time
                position['pnl'] = pnl
                position['close_reason'] = 'emergency_close'
                position['exit_price'] = current_price
                
                # Update balance
                self.balance += pnl
                
                # Move to closed positions
                self.positions.remove(position)
                self.closed_positions.append(position)
                
                # Update performance
                self.update_performance_stats(position)
                
                closed_positions.append({
                    'id': position['id'],
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'pnl': pnl,
                    'reason': 'emergency_close',
                    'timestamp': current_time
                })
        
        return closed_positions

    def get_open_positions_summary(self) -> List[Dict]:
        """Get summary of open positions for frontend"""
        summary = []
        current_time = datetime.now()
        
        for position in self.positions:
            if position.get('status') == 'open':
                time_open = current_time - position['opened_at']
                minutes_open = time_open.total_seconds() / 60
                time_remaining = max(0, 8 - minutes_open)
                
                summary.append({
                    'id': position['id'],
                    'direction': position['direction'],
                    'strategy': position['strategy'],
                    'entry_price': position['entry_price'],
                    'current_price': position.get('current_price', position['entry_price']),
                    'current_pnl': position.get('floating_profit', 0),
                    'floating_profit': position.get('floating_profit', 0),
                    'amount': position['size'],
                    'confidence': position['confidence'],
                    'timestamp': position['opened_at'],
                    'time_remaining_minutes': round(time_remaining, 1),
                    'is_near_timeout': time_remaining <= 2,
                    'stop_loss': position['stop_loss'],
                    'take_profit': position['take_profit']
                })
        return summary

    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze trading performance"""
        # Calculate floating P&L
        floating_pnl = 0
        for position in self.positions:
            if position.get('status') == 'open':
                floating_pnl += position.get('floating_profit', 0)
        
        # Get recent trades (last 10)
        recent_trades = self.closed_positions[-10:] if self.closed_positions else []
        
        return {
            'summary': {
                'total_trades': self.performance_stats['total_trades'],
                'winning_trades': self.performance_stats['winning_trades'],
                'losing_trades': self.performance_stats['losing_trades'],
                'total_profit': self.performance_stats['total_profit'],
                'win_rate': self.performance_stats['win_rate'],
                'current_balance': self.balance,
                'floating_pnl': floating_pnl,
                'equity': self.balance + floating_pnl,
                'initial_balance': self.initial_balance,
                'open_positions': len(self.positions),
                'consecutive_losses': self.consecutive_losses
            },
            'recent_trades': recent_trades,
            'strategy_stats': self.strategy_stats
        }

    def reset_daily_stats(self):
        """Reset daily statistics"""
        current_date = datetime.now().date()
        if current_date != self.daily_stats["date"]:
            self.daily_stats = {
                "date": current_date,
                "trades_today": 0,
                "pnl_today": 0.0,
                "winning_trades": 0,
                "losing_trades": 0
            }