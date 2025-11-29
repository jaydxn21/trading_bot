# bot.py - UPDATED WITH SUPER SCALPER INTEGRATION AND STRATEGY FIXES

from datetime import datetime, timedelta# MONKEY PATCH MUST BE FIRST - BEFORE ANY OTHER IMPORTS
import eventlet
eventlet.monkey_patch()

from flask import Flask, request
from flask_socketio import SocketIO, emit
import logging
from datetime import datetime
import threading
from ai_core import MLTradePredictor

import time
import json
import websocket
import os
from typing import Optional, Dict, Any
import numpy as np
import traceback

# Import your modules
import config
from utils import indicators
from trading_logic import TradingLogic
from strategies import STRATEGIES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'quantum-trader-pro-secret-key'

# FIXED: Simplified SocketIO configuration
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='eventlet'
)

class DerivTrading:
    def __init__(self, api_token: str, app_id: int = 1089):
        self.api_token = api_token
        self.app_id = app_id
        self.ws_url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        self.websocket: Optional[websocket.WebSocketApp] = None
        self.connected = False
        self.authorized = False
        self.balance: Optional[float] = None
        self.pending_requests: Dict[str, Any] = {}
        self.last_balance_update = None
        
    def connect(self) -> bool:
        """Connect to Deriv WebSocket for real trading"""
        try:
            logger.info("🔌 Connecting to Deriv Real Trading API...")
            
            self.websocket = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # Run WebSocket in separate thread
            ws_thread = threading.Thread(target=self.websocket.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection with timeout
            for i in range(15):  # 15 second timeout
                if self.connected and self.authorized:
                    logger.info("✅ Successfully connected and authorized with Deriv")
                    return True
                time.sleep(1)
            
            if not self.connected:
                logger.error("❌ Deriv connection timeout")
                return False
            if not self.authorized:
                logger.error("❌ Deriv authorization timeout")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Deriv real trading connection failed: {e}")
            return False
    
    def _on_open(self, ws):
        """WebSocket connection opened"""
        logger.info("✅ WebSocket connected to Deriv Real Trading")
        self.connected = True
        # Authorize with API token
        auth_msg = {"authorize": self.api_token}
        ws.send(json.dumps(auth_msg))
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages - FIXED VERSION"""
        try:
            msg = json.loads(message)
            logger.debug(f"📨 Deriv API response: {msg}")
            
            # Handle authorization response
            if "authorize" in msg:
                auth_response = msg["authorize"]
                if isinstance(auth_response, dict) and auth_response.get("error"):
                    error_msg = auth_response["error"]["message"]
                    logger.error(f"❌ Deriv authorization failed: {error_msg}")
                    self.authorized = False
                else:
                    logger.info("✅ Authorized with Deriv Real Account")
                    self.authorized = True
                    # FIX: Properly handle balance extraction
                    if isinstance(auth_response, dict) and "balance" in auth_response:
                        balance_data = auth_response["balance"]
                        if isinstance(balance_data, dict) and "balance" in balance_data:
                            self.balance = float(balance_data["balance"])
                            logger.info(f"💰 Real Account Balance: ${self.balance:.2f}")
            
            # Handle buy contract response
            elif "buy" in msg:
                buy_response = msg["buy"]
                if isinstance(buy_response, dict) and buy_response.get("error"):
                    error_msg = buy_response["error"]["message"]
                    logger.error(f"❌ Real trade failed: {error_msg}")
                else:
                    contract_id = buy_response.get("contract_id", "Unknown")
                    logger.info(f"✅ REAL TRADE CONFIRMED - Contract ID: {contract_id}")
                    # Update balance after trade
                    self.get_balance()
            
            # Handle balance response
            elif "balance" in msg:
                balance_response = msg["balance"]
                # FIX: Handle different balance response formats
                if isinstance(balance_response, dict) and "balance" in balance_response:
                    self.balance = float(balance_response["balance"])
                elif isinstance(balance_response, (int, float)):
                    self.balance = float(balance_response)
                
                self.last_balance_update = datetime.now()
                logger.info(f"💰 Updated Real Balance: ${self.balance:.2f}")
                
        except Exception as e:
            logger.error(f"❌ Error processing Deriv message: {e}")
            logger.error(f"📄 Problematic message: {message}")
    
    def _on_error(self, ws, error):
        logger.error(f"❌ Deriv WebSocket error: {error}")
        self.connected = False
        self.authorized = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"🔌 Deriv connection closed: {close_msg}")
        self.connected = False
        self.authorized = False
    
    def place_trade(self, symbol: str, amount: float, direction: str, 
                   duration: int = 5, duration_unit: str = "m") -> bool:
        """Place a REAL trade on Deriv platform"""
        if not self.connected or not self.authorized:
            logger.error("❌ Not connected/authorized to Deriv Real Trading")
            return False
        
        # Validate trade parameters
        if amount <= 0:
            logger.error("❌ Invalid trade amount")
            return False
        
        if direction.upper() not in ["CALL", "PUT"]:
            logger.error("❌ Invalid trade direction")
            return False
        
        trade_request = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": direction.upper(),
                "currency": "USD",
                "duration": duration,
                "duration_unit": duration_unit,
                "symbol": symbol
            }
        }
        
        try:
            self.websocket.send(json.dumps(trade_request))
            logger.info(f"🚀 Placing REAL {direction} trade: ${amount} on {symbol}")
            return True
        except Exception as e:
            logger.error(f"❌ Real trade placement failed: {e}")
            return False
    
    def get_balance(self) -> Optional[float]:
        """Get REAL account balance - FIXED VERSION"""
        if not self.connected or not self.authorized:
            logger.warning("⚠️ Not connected/authorized for balance request")
            return None
        
        balance_request = {"balance": 1}
        try:
            self.websocket.send(json.dumps(balance_request))
            # Wait a moment for the response
            time.sleep(0.5)
            return self.balance
        except Exception as e:
            logger.error(f"❌ Real balance request failed: {e}")
            return None
    
    def disconnect(self):
        """Close Deriv connection"""
        if self.websocket:
            self.websocket.close()
        self.connected = False
        self.authorized = False

class TradingBot:
    def __init__(self):
        self.connected_clients = 0
        self.trading_enabled = config.TRADING_ENABLED
        self.candles = []
        self.authorized = False
        self.subscribed = False
        self.client_lock = threading.Lock()
        self.ml_predictor = MLTradePredictor()
        self.learning_mode = True
        self.trade_history = []
        self.ai_optimizer = None  # Initialize when API key is available
        self.last_optimization = None
        
        # Initialize AI if API key available
        self._initialize_ai()
        
        # Connection management
        self.max_clients = 100
        self.max_connections_per_ip = 50
        self.client_ips = {}
        
        # 🔧 FIX: Strategy name mapping for compatibility
        self.strategy_name_mapping = {
            'enhanced_snr_adx': 'snr_adx',  # Map old name to new name
            'snr_adx': 'snr_adx',           # Keep new name
            'scalper': 'scalper',
            'emergency': 'emergency', 
            'enhanced_sma': 'enhanced_sma',
            'super_scalper': 'super_scalper'
        }
        
        # Enhanced trading logic with better risk management
        self.trading_logic = TradingLogic(
            starting_balance=config.INITIAL_BALANCE,
            risk_per_trade=config.RISK_PER_TRADE
        )
        
        # Strategy performance tracking
        self.strategy_performance = {}
        self.last_trade_time = {}
        self.daily_trade_counts = {}
        
        # SUPER SCALPER SPECIFIC TRACKING
        self.daily_burst_count = {}
        self.last_burst_result = None
        self.last_burst_time = None
        self.burst_trade_counter = 0
        
        # REAL TRADING SETUP
        self.real_trading_enabled = config.TRADE_EXECUTION == "real"
        self.deriv_trading = None
        self.daily_real_loss = 0
        self.last_real_loss_reset = datetime.now().date()
        
        # Platform management
        self.current_platform = "deriv"
        self.deriv_ws = None
        self.deriv_connected = False
        
        # Custom platform connection (placeholder)
        self.custom_connected = False

        # Initialize real trading if enabled
        if self.real_trading_enabled:
            self._initialize_real_trading()

    def _initialize_real_trading(self):
        """Initialize real Deriv trading connection"""
        try:
            if not config.API_TOKEN or config.API_TOKEN == "":
                logger.error("❌ REAL TRADING DISABLED - No API token configured")
                self.real_trading_enabled = False
                return
            
            logger.info("🎯 INITIALIZING REAL DERIV TRADING...")
            
            self.deriv_trading = DerivTrading(config.API_TOKEN, int(config.APP_ID))
            
            # Connect to Deriv API
            success = self.deriv_trading.connect()
            if success:
                logger.info("✅ REAL TRADING ENABLED - Trades will execute on Deriv platform")
                # Get initial balance
                time.sleep(3)  # Wait for connection
                balance = self.deriv_trading.get_balance()
                if balance:
                    logger.info(f"💰 INITIAL REAL ACCOUNT BALANCE: ${balance:.2f}")
            else:
                logger.error("❌ REAL TRADING DISABLED - Failed to connect to Deriv")
                self.real_trading_enabled = False
                
        except Exception as e:
            logger.error(f"❌ Real trading initialization failed: {e}")
            self.real_trading_enabled = False

    def test_real_trade(self):
        """Test real trading with a small amount"""
        if self.real_trading_enabled and self.deriv_trading:
            logger.info("🧪 TESTING REAL TRADE EXECUTION...")
            success = self.deriv_trading.place_trade(
                symbol=config.SYMBOL,
                amount=1.0,  # $1 test trade
                direction="CALL",
                duration=1,  # 1 minute
                duration_unit="m"
            )
            if success:
                logger.info("✅ REAL TRADE TEST EXECUTED - Check your Deriv account!")
            else:
                logger.error("❌ REAL TRADE TEST FAILED")
        else:
            logger.warning("⚠️ Real trading not enabled - skipping test")

    def start_connection_monitor(self):
        """Monitor and maintain connections"""
        def monitor():
            while True:
                time.sleep(30)  # Check every 30 seconds
                
                # Check Deriv connection
                if self.real_trading_enabled and self.deriv_trading:
                    if not self.deriv_trading.connected or not self.deriv_trading.authorized:
                        logger.warning("🔄 Deriv connection lost - attempting reconnect...")
                        self.deriv_trading.connect()
                
                # Sync real balance periodically
                if self.real_trading_enabled:
                    self.sync_real_trades_with_dashboard()
                    
                # Broadcast system summary
                self.broadcast_system_summary()
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()

    def ai_enhanced_execute_trade(self, strategy: str, action: str, price: float, 
                             confidence: float, indicator_data: Dict, signal: Dict = None):
        """Execute trade with AI-enhanced risk management"""
        
        # Get AI prediction
        ai_confidence = self.ml_predictor.predict_success_probability(
            self.candles, indicator_data, price, strategy
        )
        
        # Combine strategy confidence with AI confidence
        combined_confidence = (confidence * 0.7) + (ai_confidence * 100 * 0.3)
        
        logger.info(f"🤖 AI Analysis - Strategy: {confidence}% | ML: {ai_confidence:.1%} | Combined: {combined_confidence:.1f}%")
        
        # Adjust position size based on AI confidence
        base_size = self._calculate_position_size(confidence)
        ai_adjusted_size = base_size * ai_confidence
        
        # Only execute if AI confidence is reasonable
        if ai_confidence > 0.4:  # 40% minimum AI confidence
            trade_data = {
                'strategy': strategy,
                'action': action,
                'entry_price': price,
                'confidence': confidence,
                'ai_confidence': ai_confidence,
                'combined_confidence': combined_confidence,
                'position_size': ai_adjusted_size,
                'candles': self.candles[-50:],  # Last 50 candles for context
                'indicators': indicator_data,
                'timestamp': datetime.now()
            }
            
            # Store for learning
            self.trade_history.append(trade_data)
            
            # Execute the trade (your existing logic)
            return self.execute_trade(strategy, action, price, combined_confidence, indicator_data, signal)
        else:
            logger.info(f"🤖 AI blocked trade: Confidence too low ({ai_confidence:.1%})")
            return None, None

    def record_trade_outcome(self, trade_id: str, outcome: Dict):
        """Record trade outcome for ML learning"""
        # Find the trade in history
        for trade in self.trade_history:
            if trade.get('trade_id') == trade_id:
                trade['outcome'] = outcome
                trade['success'] = outcome.get('pnl', 0) > 0
                
                # Learn from this trade
                if self.learning_mode:
                    self.ml_predictor.learn_from_trade(trade, trade['success'])
                break
    def _initialize_ai(self):
        """Initialize AI components"""
        try:
            # Try to get OpenAI API key from environment
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                from ai_optimizer import AIStrategyOptimizer
                self.ai_optimizer = AIStrategyOptimizer(api_key)
                logger.info("✅ AI Optimizer initialized with OpenAI")
            else:
                logger.info("🤖 AI Optimizer: No OpenAI API key found (optional)")
                
        except Exception as e:
            logger.error(f"❌ AI initialization failed: {e}")

    def enhanced_evaluate_strategies(self, price, candles):
        """Enhanced strategy evaluation with AI filtering"""
        signals = self.evaluate_strategies(price, candles)  # Your existing method
        
        # Filter signals with AI
        ai_filtered_signals = []
        for strat, action, conf, indicators, signal in signals:
            ai_prob = self.ml_predictor.predict_success_probability(
                candles, indicators, price, strat
            )
            
            # Only include if AI confidence is reasonable
            if ai_prob > 0.4:  # 40% minimum threshold
                ai_filtered_signals.append((strat, action, conf, indicators, signal, ai_prob))
                logger.info(f"🤖 AI Approved: {strat} {action} (ML Confidence: {ai_prob:.1%})")
            else:
                logger.info(f"🤖 AI Rejected: {strat} {action} (ML Confidence: {ai_prob:.1%})")
        
        return ai_filtered_signals

    def periodic_ai_optimization(self):
        """Run AI optimization periodically"""
        def optimization_loop():
            while True:
                try:
                    # Wait 6 hours between optimizations
                    time.sleep(6 * 3600)
                    
                    if self.ai_optimizer and len(self.trade_history) >= 20:
                        logger.info("🤖 Running periodic AI optimization...")
                        
                        # Analyze performance
                        analysis = self.ai_optimizer.analyze_performance(
                            self.strategy_performance,
                            self.trade_history[-50:]  # Last 50 trades
                        )
                        
                        # Apply optimizations
                        self._apply_ai_optimizations(analysis)
                        self.last_optimization = datetime.now()
                        
                except Exception as e:
                    logger.error(f"❌ AI optimization failed: {e}")
                    time.sleep(3600)  # Wait 1 hour on error
        
        # Start optimization thread
        import threading
        opt_thread = threading.Thread(target=optimization_loop, daemon=True)
        opt_thread.start()

    def _apply_ai_optimizations(self, analysis: Dict):
        """Apply AI-suggested optimizations"""
        if 'optimizations' in analysis:
            logger.info("🎯 Applying AI optimizations...")
            # Here you would update your strategy parameters
            # based on the AI recommendations
            pass
                
    def sync_real_trades_with_dashboard(self):
        """Sync real Deriv trades with dashboard display"""
        try:
            if not self.real_trading_enabled or not self.deriv_trading:
                return
                
            logger.info("🔄 Syncing real trades with dashboard...")
            
            # Get current real balance
            real_balance = self.update_real_balance()
            if real_balance:
                # Broadcast real balance update
                self.broadcast_real_trade_status({
                    'type': 'balance_update',
                    'real_balance': real_balance,
                    'timestamp': datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"❌ Trade sync failed: {e}")

    def broadcast_real_trade_status(self, trade_data):
        """Broadcast real trade status to dashboard"""
        try:
            socketio.emit('real_trade_status', trade_data)
            
            # Also log for debugging
            if trade_data.get('type') == 'balance_update':
                logger.info(f"💰 Real balance sync: ${trade_data.get('real_balance', 0):.2f}")
                
        except Exception as e:
            logger.error(f"Error broadcasting real trade status: {e}")

    def execute_real_trade(self, strategy: str, action: str, price: float, 
                          confidence: float) -> Optional[str]:
        """Execute REAL trade on Deriv platform"""
        if not self.real_trading_enabled or not self.deriv_trading:
            return None
        
        # Check daily loss limit for real trading
        if self._check_real_daily_loss_limit():
            logger.warning("🚫 Daily REAL loss limit reached - No real trades allowed")
            return None
        
        # Convert bot signal to Deriv contract type
        direction = "CALL" if action.upper() == "BUY" else "PUT"
        
        # Calculate trade amount based on confidence and risk management
        trade_amount = self._calculate_real_trade_amount(confidence, strategy)
        
        if trade_amount <= 0:
            logger.error("❌ Invalid real trade amount calculated")
            return None
        
        # Place real trade on Deriv
        success = self.deriv_trading.place_trade(
            symbol=config.SYMBOL,
            amount=trade_amount,
            direction=direction,
            duration=5,  # 5 minute contracts for R_100
            duration_unit="m"
        )
        
        if success:
            trade_id = f"deriv_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"✅ REAL TRADE EXECUTED: {direction} ${trade_amount:.2f} on {config.SYMBOL}")
            logger.info(f"💰 Strategy: {strategy} | Confidence: {confidence:.1f}%")
            
            # Broadcast real trade execution
            self.broadcast_real_trade_execution({
                'strategy': strategy,
                'action': action,
                'price': price,
                'confidence': confidence,
                'trade_id': trade_id,
                'amount': trade_amount,
                'direction': direction,
                'timestamp': datetime.now().isoformat()
            })
            
            return trade_id
        else:
            logger.error(f"❌ REAL TRADE FAILED: {direction} ${trade_amount:.2f}")
            return None

    def _calculate_real_trade_amount(self, confidence: float, strategy: str) -> float:
        """Calculate REAL trade amount with proper risk management for R_100"""
        # Strategy-specific base amounts
        strategy_base = {
            "scalper": 1.0,
            "snr_adx": 2.0, 
            "emergency": 1.0,
            "enhanced_sma": 1.5,
            "super_scalper": 1.0  # Base amount for super scalper
        }
        
        base_amount = strategy_base.get(strategy, 1.0)
        confidence_multiplier = confidence / 100.0
        
        # Calculate amount based on confidence (scaled for R_100)
        amount = base_amount + (confidence_multiplier * 3)  # 1-4 USD range
        
        # Apply maximum trade limit from config
        max_trade_amount = float(os.getenv("MAX_TRADE_AMOUNT", "5"))
        amount = min(amount, max_trade_amount)
        
        # Ensure minimum trade amount for Deriv
        amount = max(amount, 1.0)
        
        logger.debug(f"🎯 Real trade amount: ${amount:.2f} (Confidence: {confidence:.1f}%)")
        return amount

    def _check_real_daily_loss_limit(self) -> bool:
        """Check if daily REAL loss limit has been reached"""
        # Reset daily tracker if it's a new day
        today = datetime.now().date()
        if today > self.last_real_loss_reset:
            self.daily_real_loss = 0
            self.last_real_loss_reset = today
        
        daily_loss_limit = float(os.getenv("DAILY_LOSS_LIMIT", "100"))
        return self.daily_real_loss >= daily_loss_limit

    def update_real_balance(self):
        """Update and display real account balance"""
        if self.real_trading_enabled and self.deriv_trading:
            balance = self.deriv_trading.get_balance()
            if balance:
                logger.info(f"💰 CURRENT REAL BALANCE: ${balance:.2f}")
                return balance
        return None

    def broadcast_real_trade_execution(self, trade_data):
        """Broadcast real trade execution to frontend"""
        try:
            socketio.emit('real_trade_executed', trade_data)
        except Exception as e:
            logger.error(f"Error broadcasting real trade: {e}")

    # SUPER SCALPER METHODS
    def can_execute_super_burst(self):
        """Check if super scalper can execute a burst"""
        # Check daily burst limit
        today = datetime.now().date()
        bursts_today = self.daily_burst_count.get(today, 0)
        if bursts_today >= config.SUPER_SCALPER_CONFIG["max_daily_bursts"]:
            logger.info("🚫 Daily burst limit reached")
            return False
            
        # Check cooldown after losing burst
        if self.last_burst_result == "loss":
            time_since_loss = (datetime.now() - self.last_burst_time).total_seconds() / 60
            if time_since_loss < config.SUPER_SCALPER_CONFIG["cooldown_after_loss"]:
                logger.info(f"⏳ Cooldown after loss: {int(config.SUPER_SCALPER_CONFIG['cooldown_after_loss'] - time_since_loss)}min remaining")
                return False
            
        # Check overall exposure
        open_super_trades = [p for p in self.trading_logic.positions 
                            if "super_scalper" in p.get("strategy", "")]
        if len(open_super_trades) >= 5:
            logger.info("🚫 Maximum super scalper positions open")
            return False
            
        return True

    def execute_super_scalper_burst(self, strategy, action, price, confidence, signal_data):
        """Execute a burst of 5 simultaneous trades for super scalper"""
        if not self.can_execute_super_burst():
            return []
            
        burst_trades = signal_data.get('burst_trades', 5)
        target_percent = signal_data.get('target_percent', 20)
        
        executed_trades = []
        
        logger.info(f"🚀 SUPER SCALPER BURST INITIATED: {action.upper()} x{burst_trades} @ ${price:.2f}")
        
        for i in range(burst_trades):
            # Slightly vary entry price for realistic execution
            varied_price = price * (1 + (np.random.random() - 0.5) * 0.0005)  # ±0.05% variation
            
            # Calculate dynamic stake based on trade number
            base_stake = self._calculate_super_scalper_stake(confidence, i)
            
            # Execute trade with 20% profit target
            trade_id = self._execute_super_trade(
                strategy=strategy,
                action=action,
                price=varied_price,
                stake=base_stake,
                target_percent=target_percent,
                trade_index=i
            )
            
            if trade_id:
                executed_trades.append(trade_id)
                
        # Update burst tracking
        today = datetime.now().date()
        self.daily_burst_count[today] = self.daily_burst_count.get(today, 0) + 1
        self.last_burst_time = datetime.now()
        self.burst_trade_counter += burst_trades
            
        logger.info(f"🚀 SUPER SCALPER BURST COMPLETED: Executed {len(executed_trades)}/{burst_trades} trades")
        return executed_trades

    def _calculate_super_scalper_stake(self, confidence, trade_index):
        """Calculate stake amount for super scalper burst trades"""
        # Base stake with confidence multiplier
        base_stake = 1.0  # $1 minimum
        
        # Confidence boost (75% confidence = 1.5x base)
        confidence_multiplier = confidence / 50  # 75/50 = 1.5
        
        # Progressive stake sizing (first trade smallest, last trade largest)
        progression_multiplier = 1.0 + (trade_index * 0.2)  # 1.0, 1.2, 1.4, 1.6, 1.8
        
        stake = base_stake * confidence_multiplier * progression_multiplier
        
        # Apply maximum limits
        max_stake = config.SUPER_SCALPER_CONFIG["max_stake_per_trade"]
        stake = min(stake, max_stake)
        
        return max(stake, 1.0)  # Ensure minimum $1

    def _execute_super_trade(self, strategy, action, price, stake, target_percent, trade_index):
        """Execute individual super scalper trade"""
        # Calculate ultra-tight stop loss and take profit
        if action == "buy":
            stop_loss = price * (1 - config.SUPER_SCALPER_CONFIG["stop_loss_percent"] / 100)
            take_profit = price * (1 + target_percent / 100)  # 20% profit target
            direction = "buy"
        else:
            stop_loss = price * (1 + config.SUPER_SCALPER_CONFIG["stop_loss_percent"] / 100)
            take_profit = price * (1 - target_percent / 100)  # 20% profit target
            direction = "sell"
        
        # Very short duration for quick scalps
        duration = config.SUPER_SCALPER_CONFIG["max_trade_duration"] // 60  # Convert to minutes
        
        volatility = 0.003  # Assumed low volatility for scalping
        
        # Execute REAL trade first
        real_trade_id = None
        if self.real_trading_enabled:
            real_trade_id = self._execute_super_real_trade(
                action=action,
                stake=stake,
                duration=duration
            )
        
        # Simulated trade for tracking
        position_id = self.trading_logic.open_position(
            direction=direction,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=f"{strategy}_burst_{trade_index}",
            trade_cost=0.001,  # Lower cost for scalping
            confidence=75,
            volatility=volatility,
            duration_minutes=duration
        )
        
        if position_id or real_trade_id:
            logger.info(f"⚡ SUPER TRADE {trade_index+1}: {action} ${stake:.2f} @ {price:.2f}")
            
            # Broadcast super trade execution
            self.broadcast_super_trade({
                'trade_index': trade_index,
                'total_trades': 5,
                'action': action,
                'stake': stake,
                'price': price,
                'target_percent': target_percent,
                'duration': duration,
                'real_trade_id': real_trade_id,
                'timestamp': datetime.now().isoformat()
            })
            
        return position_id or real_trade_id

    def _execute_super_real_trade(self, action, stake, duration):
        """Execute real super scalper trade on Deriv"""
        if not self.real_trading_enabled or not self.deriv_trading:
            return None
            
        direction = "CALL" if action == "buy" else "PUT"
        
        success = self.deriv_trading.place_trade(
            symbol=config.SYMBOL,
            amount=stake,
            direction=direction,
            duration=duration,
            duration_unit="m"
        )
        
        if success:
            trade_id = f"super_{datetime.now().strftime('%H%M%S')}_{direction}"
            logger.info(f"✅ REAL SUPER TRADE: {direction} ${stake:.2f}")
            return trade_id
        return None

    def broadcast_super_trade(self, trade_data):
        """Broadcast super scalper trade to frontend"""
        try:
            socketio.emit('super_trade_executed', trade_data)
        except Exception as e:
            logger.error(f"Error broadcasting super trade: {e}")

    def start_deriv_connection(self):
        """Start connection to Deriv API with better reconnection handling."""
        def run_deriv_ws():
            reconnect_delay = 5  # Start with 5 seconds
            max_reconnect_delay = 60  # Max 60 seconds
            
            while True:
                try:
                    logger.info("🚀 Starting Deriv WebSocket connection...")
                    
                    self.deriv_ws = websocket.WebSocketApp(
                        config.DERIV_WS_URL,
                        on_message=self.on_deriv_message,
                        on_error=self.on_deriv_error,
                        on_close=self.on_deriv_close,
                        on_open=self.on_deriv_open
                    )
                    
                    # FIXED: Removed ping_timeout parameter
                    self.deriv_ws.run_forever()
                    
                except Exception as e:
                    logger.error(f"❌ Deriv connection failed: {e}")
                
                # Exponential backoff for reconnection
                logger.info(f"🔄 Reconnecting in {reconnect_delay} seconds...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                    
        deriv_thread = threading.Thread(target=run_deriv_ws, daemon=True)
        deriv_thread.start()

    def deriv_heartbeat(self):
        """Separate heartbeat thread."""
        while True:
            time.sleep(20)
            try:
                if self.deriv_ws and self.deriv_connected:
                    self.deriv_ws.send(json.dumps({"ping": 1}))
            except Exception as e:
                logger.error(f"❤️ Heartbeat failed: {e}")
                self.deriv_connected = False

    def on_deriv_open(self, ws):
        logger.info("🔌 WebSocket connected to Deriv API")
        self.deriv_connected = True
        heartbeat_thread = threading.Thread(target=self.deriv_heartbeat, daemon=True)
        heartbeat_thread.start()
        ws.send(json.dumps({"authorize": config.API_TOKEN}))

    def on_deriv_message(self, ws, message):
        try:
            msg = json.loads(message)
            
            if "authorize" in msg:
                if msg["authorize"].get("error"):
                    logger.error(f"❌ Authorization failed: {msg['authorize']['error']['message']}")
                    return
                else:
                    self.authorized = True
                    logger.info("✅ Successfully authorized with Deriv API")
                    subscribe_msg = {"ticks": config.SYMBOL}
                    ws.send(json.dumps(subscribe_msg))
                    logger.info(f"📡 Sent subscription request for {config.SYMBOL}")
                    return

            if "tick" in msg:
                tick_data = msg["tick"]
                
                if not self.subscribed:
                    self.subscribed = True
                    logger.info(f"✅ Successfully subscribed to {config.SYMBOL} - receiving live data")
                
                if "quote" in tick_data:
                    price = float(tick_data["quote"])
                    self.process_tick(price)
                    
        except Exception as e:
            logger.error(f"❌ Error processing Deriv message: {e}")

    def on_deriv_error(self, ws, error):
        logger.error(f"❌ Deriv WebSocket error: {error}")
        self.deriv_connected = False

    def on_deriv_close(self, ws, close_status_code, close_msg):
        logger.warning(f"🔌 Deriv WebSocket closed: {close_status_code} - {close_msg}")
        self.deriv_connected = False
        self.authorized = False
        self.subscribed = False

    def close_all_open_trades(self, current_price: float):
        """Emergency close all open trades."""
        closed_positions = self.trading_logic.close_all_open_trades(current_price)
        if closed_positions:
            logger.info(f"🚨 EMERGENCY CLOSE: Closed {len(closed_positions)} trades")
        return closed_positions

    def can_strategy_trade(self, strategy: str) -> bool:
        """Enhanced strategy trading permission with cooldown and performance checks."""
        if not self.trading_enabled:
            return False
            
        # Special handling for super scalper burst trades
        if strategy == "super_scalper":
            return self.can_execute_super_burst()
            
        # Check strategy cooldown
        current_time = datetime.now()
        if strategy in self.last_trade_time:
            time_since_last = (current_time - self.last_trade_time[strategy]).total_seconds()
            strategy_config = config.STRATEGY_CONFIG.get(strategy, {})
            min_cooldown = strategy_config.get("min_time_between_trades", 180)
            if time_since_last < min_cooldown:
                logger.info(f"⏳ Strategy {strategy} in cooldown ({int(min_cooldown - time_since_last)}s remaining)")
                return False
        
        # Check daily trade limit
        today = datetime.now().date()
        if strategy not in self.daily_trade_counts:
            self.daily_trade_counts[strategy] = {"date": today, "count": 0}
        
        if self.daily_trade_counts[strategy]["date"] != today:
            self.daily_trade_counts[strategy] = {"date": today, "count": 0}
            
        daily_limit = config.STRATEGY_CONFIG.get(strategy, {}).get("daily_trade_limit", 10)
        if self.daily_trade_counts[strategy]["count"] >= daily_limit:
            logger.info(f"📊 Strategy {strategy} reached daily limit ({self.daily_trade_counts[strategy]['count']}/{daily_limit})")
            return False
        
        # Check open positions limit
        open_positions = self.trading_logic.get_open_positions_summary()
        strategy_positions = [p for p in open_positions if p["strategy"] == strategy]
        max_positions = config.get_max_open_positions(strategy)
        
        if len(strategy_positions) >= max_positions:
            logger.info(f"📊 Strategy {strategy} at max positions ({len(strategy_positions)}/{max_positions})")
            return False
            
        # Check strategy performance
        if strategy in self.strategy_performance:
            perf = self.strategy_performance[strategy]
            if perf.get("consecutive_losses", 0) >= config.MAX_CONSECUTIVE_LOSSES:
                logger.warning(f"🔻 Strategy {strategy} has {perf['consecutive_losses']} consecutive losses - pausing")
                return False
                
        return True

    def update_strategy_performance(self, strategy: str, pnl: float):
        """Update strategy performance tracking."""
        if strategy not in self.strategy_performance:
            self.strategy_performance[strategy] = {
                "total_trades": 0,
                "winning_trades": 0,
                "total_pnl": 0.0,
                "consecutive_losses": 0,
                "consecutive_wins": 0,
                "win_rate": 0.0
            }
        
        perf = self.strategy_performance[strategy]
        perf["total_trades"] += 1
        perf["total_pnl"] += pnl
        
        if pnl > 0:
            perf["winning_trades"] += 1
            perf["consecutive_wins"] += 1
            perf["consecutive_losses"] = 0
        else:
            perf["consecutive_losses"] += 1
            perf["consecutive_wins"] = 0
        
        perf["win_rate"] = (perf["winning_trades"] / perf["total_trades"] * 100) if perf["total_trades"] > 0 else 0

    def process_tick(self, price):
        """Enhanced tick processing with proper candle formation and real trade sync"""
        try:
            # Update trading logic with current price
            self.trading_logic.update_price(price)
            
            # Create proper candle structure
            current_time = datetime.now()
            current_candle = None
            
            if self.candles:
                last_candle = self.candles[-1]
                if last_candle['timestamp'].minute == current_time.minute:
                    last_candle['high'] = max(last_candle['high'], price)
                    last_candle['low'] = min(last_candle['low'], price)
                    last_candle['close'] = price
                    last_candle['volume'] += 1
                    current_candle = last_candle
                else:
                    current_candle = {
                        'open': price,
                        'high': price,
                        'low': price,
                        'close': price,
                        'volume': 1,
                        'timestamp': current_time
                    }
                    self.candles.append(current_candle)
            else:
                current_candle = {
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': 1,
                    'timestamp': current_time
                }
                self.candles.append(current_candle)
            
            # Broadcast candle update
            if current_candle:
                self.broadcast_candle_update(current_candle)
            
            # Keep only recent candles
            if len(self.candles) > config.HISTORY_COUNT:
                self.candles = self.candles[-config.HISTORY_COUNT:]
            
            # 🔄 SYNC REAL TRADES WITH DASHBOARD
            if len(self.candles) % 10 == 0:  # Sync every 10 candles
                self.sync_real_trades_with_dashboard()
            
            # Manage existing positions FIRST
            closed_positions = self.trading_logic.manage_open_positions(price)
            if closed_positions:
                for pos in closed_positions:
                    self.update_strategy_performance(pos["strategy"], pos["pnl"])
                self.broadcast_closed_positions(closed_positions)
            
            # Evaluate strategies if we have enough data
            if len(self.candles) >= 20:
                signals = self.evaluate_strategies(price, self.candles)
                for strat, action, conf, indicator_data, signal in signals:
                    if self.can_strategy_trade(strat):
                        # Special handling for super scalper burst trades
                        if strat == "super_scalper" and signal.get('burst_trades'):
                            executed_trades = self.execute_super_scalper_burst(
                                strat, action, price, conf, signal
                            )
                            if executed_trades:
                                self.last_trade_time[strat] = datetime.now()
                                if strat in self.daily_trade_counts:
                                    self.daily_trade_counts[strat]["count"] += len(executed_trades)
                        else:
                            # Normal trade execution for other strategies
                            position_id, real_trade_id = self.execute_trade(strat, action, price, conf, indicator_data, signal)
                            if position_id:
                                self.last_trade_time[strat] = datetime.now()
                                if strat in self.daily_trade_counts:
                                    self.daily_trade_counts[strat]["count"] += 1
                    
                    # Broadcast signal for frontend display
                    self.broadcast_trading_cycle({
                        'signal': action.lower(),
                        'confidence': conf,
                        'reason': signal.get('reason', ''),
                        'strategy': strat,
                        'price': price,
                        'market_regime': 'active',
                        'emergency': False
                    })
            
            # Broadcast system summary periodically
            if len(self.candles) % 30 == 0:
                self.broadcast_system_summary()
                
        except Exception as e:
            logger.error(f"❌ Error processing tick: {e}")
            logger.error(traceback.format_exc())

    def evaluate_strategies(self, price, candles):
        """Enhanced strategy evaluation with performance filtering."""
        if len(candles) < 20:
            return []
        
        signals = []
        
        # Extract price arrays for indicators
        closes = np.array([c['close'] for c in candles])
        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        
        try:
            indicator_data = self.debug_calculate_indicators(highs, lows, closes)
            logger.info(f"📊 Indicators - RSI: {indicator_data['rsi']:.1f}, ADX: {indicator_data['adx']:.1f}")
                
        except Exception as e:
            logger.error(f"❌ Indicator calculation failed: {e}")
            return []
        
        # Evaluate each active strategy with performance checks
        for strat_name in config.ACTIVE_STRATEGIES:
            # 🔧 FIX: Use strategy name mapping
            actual_strat_name = self.strategy_name_mapping.get(strat_name, strat_name)
            
            if actual_strat_name in self.strategy_performance:
                perf = self.strategy_performance[actual_strat_name]
                if perf.get("consecutive_losses", 0) >= config.MAX_CONSECUTIVE_LOSSES:
                    logger.info(f"⏸️ Skipping {actual_strat_name} - {perf['consecutive_losses']} consecutive losses")
                    continue
            
            strategy_instance = STRATEGIES.get(actual_strat_name)
            
            if not strategy_instance:
                logger.warning(f"❌ Strategy {strat_name} -> {actual_strat_name} not found")
                continue
                
            settings = config.STRATEGY_CONFIG.get(strat_name, {})
            if not settings.get("enabled", False):
                continue
            
            try:
                signal = strategy_instance.analyze_market(candles, price, indicator_data)
                
                if signal and signal.get("signal") in ["buy", "sell"]:
                    confidence = signal.get("confidence", 0)
                    action = signal.get("signal", "").upper()
                    reason = signal.get("reason", "")
                    
                    strategy_min_confidence = settings.get("min_confidence", config.MIN_CONFIDENCE)
                    
                    if confidence >= strategy_min_confidence:
                        if self.is_good_market_condition(indicator_data, action, actual_strat_name):
                            signals.append((actual_strat_name, action, confidence, indicator_data, signal))
                            logger.info(f"🎯 {actual_strat_name.upper()} SIGNAL: {action} (confidence: {confidence}%)")
                        else:
                            logger.info(f"🌊 {actual_strat_name.upper()} signal filtered - poor market conditions")
                        
            except Exception as e:
                logger.error(f"❌ Strategy {actual_strat_name} evaluation failed: {e}")
        
        return signals

    def debug_calculate_indicators(self, highs, lows, closes):
        """Debug version to identify ADX calculation issues"""
        logger.info(f"[DEBUG] Input sizes - Highs: {len(highs)}, Lows: {len(lows)}, Closes: {len(closes)}")
        
        if len(closes) < 14:
            logger.warning("[DEBUG] Insufficient data for ADX calculation")
            return {
                'rsi': 50.0,
                'adx': 0.0,
                'sma_fast': np.mean(closes) if len(closes) > 0 else 0,
                'sma_slow': np.mean(closes) if len(closes) > 0 else 0,
                'bb_upper': np.mean(closes) if len(closes) > 0 else 0,
                'bb_lower': np.mean(closes) if len(closes) > 0 else 0,
                'bb_middle': np.mean(closes) if len(closes) > 0 else 0,
                'volatility': 0.002,
                'support_resistance': {'support': min(closes) if len(closes) > 0 else 0, 'resistance': max(closes) if len(closes) > 0 else 0}
            }
        
        try:
            # Simple RSI calculation
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
            avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)
            
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
            
            # Simple ADX approximation for debugging
            price_range = max(highs) - min(lows)
            if price_range > 0:
                recent_volatility = np.std(closes[-14:]) / np.mean(closes[-14:])
                adx = min(100.0, recent_volatility * 1000)
            else:
                adx = 0.0
                
            logger.info(f"[DEBUG] Calculated RSI: {rsi:.2f}, ADX: {adx:.2f}")
            
            return {
                'rsi': float(rsi),
                'adx': float(adx),
                'sma_fast': float(np.mean(closes[-10:])),
                'sma_slow': float(np.mean(closes[-20:])),
                'bb_upper': float(np.mean(closes) + 2 * np.std(closes)),
                'bb_lower': float(np.mean(closes) - 2 * np.std(closes)),
                'bb_middle': float(np.mean(closes)),
                'volatility': float(np.std(closes) / np.mean(closes) if np.mean(closes) > 0 else 0.002),
                'support_resistance': {
                    'support': float(np.min(closes[-20:])),
                    'resistance': float(np.max(closes[-20:]))
                }
            }
            
        except Exception as e:
            logger.error(f"[DEBUG] Indicator calculation error: {e}")
            return {
                'rsi': 50.0,
                'adx': 25.0,
                'sma_fast': np.mean(closes) if len(closes) > 0 else 0,
                'sma_slow': np.mean(closes) if len(closes) > 0 else 0,
                'bb_upper': np.mean(closes) if len(closes) > 0 else 0,
                'bb_lower': np.mean(closes) if len(closes) > 0 else 0,
                'bb_middle': np.mean(closes) if len(closes) > 0 else 0,
                'volatility': 0.002,
                'support_resistance': {'support': min(closes) if len(closes) > 0 else 0, 'resistance': max(closes) if len(closes) > 0 else 0}
            }

    def is_good_market_condition(self, indicator_data: dict, action: str, strategy: str) -> bool:
        """Enhanced market condition filtering that works with low ADX markets."""
        rsi = indicator_data.get('rsi', 50)
        adx = indicator_data.get('adx', 20)
        volatility = indicator_data.get('volatility', 0.002)
        
        # For very low ADX markets (ranging), use different logic
        if adx < 10:
            logger.info(f"📊 Ranging market detected (ADX: {adx:.1f}) - using range strategies")
            
            # In ranging markets, look for RSI extremes
            if action == "BUY" and rsi < 35:
                return True
            elif action == "SELL" and rsi > 65:
                return True
            return False
        
        # Original V100 logic for trending markets
        if adx < config.V100_OPTIMIZED["min_adx"]:
            logger.info(f"📊 ADX too weak for V100: {adx:.1f} < {config.V100_OPTIMIZED['min_adx']}")
            return False
            
        # RSI filter using V100 ranges
        rsi_min, rsi_max = config.V100_OPTIMIZED["rsi_filter_range"]
        if rsi < rsi_min or rsi > rsi_max:
            logger.info(f"📈 RSI outside V100 optimal range: {rsi:.1f} not in {rsi_min}-{rsi_max}")
            return False
            
        # Filter out trades in low volatility markets
        if volatility < 0.0002:
            logger.info("🌊 Market too calm - skipping trade")
            return False
            
        # Filter out trades in extremely high volatility
        if volatility > 0.01:
            logger.info("🌪️ Market too volatile - skipping trade")
            return False
            
        # Strategy-specific filters
        if strategy == "scalper":
            if volatility < 0.002:
                return False
        elif strategy == "snr_adx":
            if volatility < 0.0015 or adx < 20:
                return False
        elif strategy == "super_scalper":
            # Tighter filters for super scalper
            if volatility < 0.001 or volatility > 0.005:
                return False
            if adx < 12:  # Require some trend for burst trades
                return False
                
        # V100 optimal time check
        if not config.is_v100_optimal_time():
            logger.info("⏰ Outside V100 optimal trading hours")
            return False
            
        return True

    def execute_trade(self, strategy, action, price, confidence, indicator_data, signal=None):
        """Enhanced trade execution with REAL trading - FIXED VERSION"""
        try:
            # Get strategy-specific risk parameters from config
            risk_params = config.STRATEGY_RISK_PARAMS.get(strategy, {})
            stop_loss_pct = risk_params.get("stop_loss_percent", config.STOP_LOSS_PERCENT)
            take_profit_pct = risk_params.get("take_profit_percent", config.TAKE_PROFIT_PERCENT)
            
            # Calculate stop loss and take profit with minimum 1.5:1 risk-reward
            if action == "BUY":
                stop_loss = price * (1 - stop_loss_pct / 100)
                min_take_profit = price + (price - stop_loss) * 1.5
                take_profit = max(price * (1 + take_profit_pct / 100), min_take_profit)
                direction = "buy"
            else:
                stop_loss = price * (1 + stop_loss_pct / 100)
                min_take_profit = price - (stop_loss - price) * 1.5
                take_profit = min(price * (1 - take_profit_pct / 100), min_take_profit)
                direction = "sell"
            
            volatility = indicator_data.get("volatility", 0.002)
            reason = signal.get("reason", "") if signal else f"{strategy} {action}"
            
            # Calculate actual risk-reward ratio
            if action == "BUY":
                risk = price - stop_loss
                reward = take_profit - price
            else:
                risk = stop_loss - price
                reward = price - take_profit
            
            risk_reward_ratio = reward / risk if risk > 0 else 0
            
            # Only execute if risk-reward meets minimum and volatility is acceptable
            if risk_reward_ratio >= 1.5 and 0.001 <= volatility <= 0.01:
                
                # 🔥 CRITICAL FIX: Execute REAL trade FIRST
                real_trade_id = None
                if self.real_trading_enabled:
                    real_trade_id = self.execute_real_trade(
                        strategy=strategy,
                        action=action,
                        price=price,
                        confidence=confidence
                    )
                    
                    # If real trade failed, don't create simulated trade
                    if not real_trade_id:
                        logger.error(f"❌ Real trade failed - skipping simulated trade for {strategy}")
                        return None, None
                
                # Simulated trade for tracking (only if real trade succeeded or real trading disabled)
                position_id = self.trading_logic.open_position(
                    direction=direction,
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    strategy=strategy,
                    trade_cost=config.TRADE_COST_PERCENT / 100,
                    confidence=confidence,
                    volatility=volatility
                )
                
                if position_id or real_trade_id:
                    trade_type = "REAL" if real_trade_id else "SIMULATION"
                    logger.info(f"🚀 EXECUTED {trade_type} {strategy} {action} at {price} - R/R: {risk_reward_ratio:.2f}")
                    
                    # Enhanced broadcast with real trade info
                    trade_data = {
                        'signal': action.lower(),
                        'confidence': confidence,
                        'reason': reason,
                        'strategy': strategy,
                        'price': price,
                        'risk_reward_ratio': risk_reward_ratio,
                        'trade_executed': {
                            'id': position_id,
                            'real_trade_id': real_trade_id,
                            'type': direction,
                            'entry_price': price,
                            'confidence': confidence,
                            'strategy': strategy,
                            'reason': reason,
                            'is_real': real_trade_id is not None,
                            'timestamp': datetime.now().isoformat()
                        }
                    }
                    
                    # Add real trade specific data
                    if real_trade_id:
                        trade_data['real_trade'] = {
                            'trade_id': real_trade_id,
                            'amount': self._calculate_real_trade_amount(confidence, strategy),
                            'direction': "CALL" if action.upper() == "BUY" else "PUT",
                            'status': 'executed'
                        }
                    
                    self.broadcast_trading_cycle(trade_data)
                    return position_id, real_trade_id
            else:
                logger.warning(f"⚠️ Trade skipped: R/R {risk_reward_ratio:.2f} or volatility {volatility:.4f} not optimal")
                return None, None
                
        except Exception as e:
            logger.error(f"❌ Trade execution failed for {strategy}: {e}")
            
        return None, None

    def broadcast_trading_cycle(self, signal_data):
        """Broadcast trading cycle information to all clients."""
        try:
            if self.connected_clients == 0:
                return
                
            socketio.emit('trading_cycle', signal_data)
        except Exception as e:
            logger.error(f"Error broadcasting trading cycle: {e}")

    def broadcast_candle_update(self, candle_data):
        """Broadcast candle updates to all clients with proper timestamp handling."""
        try:
            if self.connected_clients == 0:
                return
                
            timestamp = candle_data.get('timestamp')
            if isinstance(timestamp, datetime):
                timestamp = int(timestamp.timestamp())
            elif timestamp is None:
                timestamp = int(datetime.now().timestamp())
                
            formatted_candle = {
                'time': timestamp,
                'open': float(candle_data.get('open', 0)),
                'high': float(candle_data.get('high', 0)),
                'low': float(candle_data.get('low', 0)),
                'close': float(candle_data.get('close', 0)),
                'volume': float(candle_data.get('volume', 1000))
            }
            socketio.emit('candle_update', formatted_candle)
        except Exception as e:
            logger.error(f"❌ Error broadcasting candle update: {e}")

    def broadcast_system_summary(self):
        """Enhanced system summary with REAL trading information"""
        try:
            if self.connected_clients == 0:
                return
                
            open_positions = self.trading_logic.get_open_positions_summary()
            
            # Calculate floating P&L safely
            floating_pnl = 0
            if open_positions:
                for pos in open_positions:
                    floating_pnl += pos.get("current_pnl", 0)
            
            # Enhanced performance data with safe cleaning
            performance = self.trading_logic.analyze_performance()
            if performance and isinstance(performance, dict) and 'summary' in performance:
                performance_summary = self.deep_clean_dict(performance['summary'])
                performance_summary['strategy_performance'] = self.clean_strategy_performance()
                performance_summary['daily_trade_counts'] = self.clean_daily_trade_counts()
            else:
                performance_summary = {
                    'total_trades': 0,
                    'win_rate': 0,
                    'total_profit': 0,
                    'recent_trades': [],
                    'strategy_performance': self.clean_strategy_performance(),
                    'daily_trade_counts': self.clean_daily_trade_counts()
                }
            
            # Get real balance if available
            real_balance = self.update_real_balance()
            
            # Enhanced summary with real trading info
            summary = {
                'portfolio': {
                    'balance': float(self.trading_logic.balance),
                    'equity': float(self.trading_logic.balance + floating_pnl),
                    'initialBalance': float(config.INITIAL_BALANCE),
                    'floating_pnl': float(floating_pnl),
                    'real_balance': float(real_balance) if real_balance else None,
                    'real_trading_enabled': self.real_trading_enabled
                },
                'open_trades': self.sanitize_trades_data(open_positions),
                'performance': performance_summary,
                'timestamp': datetime.now().isoformat(),
                'trading_enabled': bool(self.trading_enabled),
                'strategy_stats': self.clean_strategy_performance(),
                'v100_optimized': config.V100_OPTIMIZED,
                'platform_info': self.get_platform_info(),
                'real_trading_enabled': self.real_trading_enabled,
                'real_trading_status': {
                    'connected': self.deriv_trading.connected if self.deriv_trading else False,
                    'authorized': self.deriv_trading.authorized if self.deriv_trading else False,
                    'balance': real_balance,
                    'last_update': self.deriv_trading.last_balance_update.isoformat() if self.deriv_trading and self.deriv_trading.last_balance_update else None
                },
                'super_scalper_stats': {
                    'daily_bursts': self.daily_burst_count.get(datetime.now().date(), 0),
                    'last_burst_result': self.last_burst_result,
                    'burst_trade_counter': self.burst_trade_counter,
                    'max_daily_bursts': config.SUPER_SCALPER_CONFIG["max_daily_bursts"]
                }
            }
            
            serializable_summary = self.convert_datetimes_to_strings(summary)
            
            try:
                json.dumps(serializable_summary)
                socketio.emit('system_summary', serializable_summary)
            except (TypeError, ValueError) as e:
                logger.error(f"❌ JSON serialization error: {e}")
                return
                
        except Exception as e:
            logger.error(f"Error broadcasting system summary: {e}")

    def convert_datetimes_to_strings(self, obj):
        """Recursively convert datetime objects to strings with comprehensive type handling."""
        try:
            if isinstance(obj, dict):
                return {k: self.convert_datetimes_to_strings(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [self.convert_datetimes_to_strings(item) for item in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif isinstance(obj, (np.integer, np.int8, np.int16, np.int32, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif obj is None:
                return None
            else:
                return obj
        except Exception as e:
            logger.warning(f"⚠️ Error converting object {type(obj)}: {e}")
            return str(obj)

    def deep_clean_dict(self, obj):
        """Deep clean a dictionary for JSON serialization."""
        if not isinstance(obj, dict):
            return obj
        
        cleaned = {}
        for key, value in obj.items():
            if isinstance(value, dict):
                cleaned[key] = self.deep_clean_dict(value)
            elif isinstance(value, (list, tuple)):
                cleaned[key] = [self.deep_clean_dict(item) if isinstance(item, dict) else self.clean_single_value(item) for item in value]
            elif isinstance(value, datetime):
                cleaned[key] = value.isoformat()
            elif hasattr(value, 'isoformat'):
                try:
                    cleaned[key] = value.isoformat()
                except:
                    cleaned[key] = str(value)
            elif isinstance(value, (np.integer, np.int8, np.int16, np.int32, np.int64)):
                cleaned[key] = int(value)
            elif isinstance(value, (np.floating, np.float16, np.float32, np.float64)):
                cleaned[key] = float(value)
            elif isinstance(value, np.bool_):
                cleaned[key] = bool(value)
            elif isinstance(value, np.ndarray):
                cleaned[key] = value.tolist()
            elif value is None:
                cleaned[key] = None
            else:
                cleaned[key] = value
        return cleaned

    def clean_single_value(self, value):
        """Clean a single value for JSON serialization."""
        if isinstance(value, datetime):
            return value.isoformat()
        elif hasattr(value, 'isoformat'):
            try:
                return value.isoformat()
            except:
                return str(value)
        elif isinstance(value, (np.integer, np.int8, np.int16, np.int32, np.int64)):
            return int(value)
        elif isinstance(value, (np.floating, np.float16, np.float32, np.float64)):
            return float(value)
        elif isinstance(value, np.bool_):
            return bool(value)
        elif isinstance(value, np.ndarray):
            return value.tolist()
        elif value is None:
            return None
        else:
            return value

    def clean_strategy_performance(self):
        """Clean strategy performance data for JSON serialization."""
        cleaned = {}
        for strategy, perf in self.strategy_performance.items():
            cleaned[strategy] = {
                "total_trades": int(perf.get("total_trades", 0)),
                "winning_trades": int(perf.get("winning_trades", 0)),
                "total_pnl": float(perf.get("total_pnl", 0.0)),
                "consecutive_losses": int(perf.get("consecutive_losses", 0)),
                "consecutive_wins": int(perf.get("consecutive_wins", 0)),
                "win_rate": float(perf.get("win_rate", 0.0))
            }
        return cleaned

    def clean_daily_trade_counts(self):
        """Clean daily trade counts for JSON serialization."""
        cleaned = {}
        for strategy, count_data in self.daily_trade_counts.items():
            cleaned[strategy] = {
                "date": count_data.get("date", datetime.now().date()).isoformat() if hasattr(count_data.get("date"), 'isoformat') else str(count_data.get("date", "")),
                "count": int(count_data.get("count", 0))
            }
        return cleaned

    def sanitize_trades_data(self, trades):
        """Sanitize trades data to ensure JSON serialization."""
        if not trades:
            return []
        
        sanitized = []
        for trade in trades:
            try:
                sanitized_trade = {}
                for key, value in trade.items():
                    sanitized_trade[key] = self.clean_single_value(value)
                
                required_fields = {
                    'id': '',
                    'direction': '',
                    'strategy': '',
                    'entry_price': 0.0,
                    'current_price': 0.0,
                    'current_pnl': 0.0,
                    'floating_profit': 0.0,
                    'amount': 0.0,
                    'confidence': 0.0,
                    'timestamp': datetime.now().isoformat(),
                    'time_remaining_minutes': 8.0,
                    'is_near_timeout': False
                }
                
                for field, default in required_fields.items():
                    if field not in sanitized_trade:
                        sanitized_trade[field] = default
                
                sanitized.append(sanitized_trade)
                
            except (TypeError, ValueError) as e:
                logger.warning(f"⚠️ Skipping invalid trade data: {trade}, error: {e}")
                continue
        
        return sanitized

    def broadcast_closed_positions(self, closed_positions):
        """Broadcast closed positions."""
        try:
            if self.connected_clients == 0:
                return
                
            serializable_closed_positions = self.convert_datetimes_to_strings(closed_positions)
            
            self.broadcast_trading_cycle({
                'signal': 'hold',
                'confidence': 0,
                'reason': 'Position management',
                'strategy': 'system',
                'closed_positions': serializable_closed_positions
            })
        except Exception as e:
            logger.error(f"Error broadcasting closed positions: {e}")

    def get_platform_info(self):
        """Get current platform information"""
        return {
            'current_platform': self.current_platform,
            'deriv_connected': self.deriv_connected if self.current_platform == 'deriv' else False,
            'custom_connected': self.custom_connected if self.current_platform == 'custom' else False,
            'authorized': self.authorized,
            'subscribed': self.subscribed,
            'real_trading_enabled': self.real_trading_enabled,
            'real_balance': self.deriv_trading.balance if self.deriv_trading else None
        }

    def switch_platform(self, platform_name: str) -> bool:
        """Switch between Deriv and custom trading platforms"""
        if platform_name not in ["deriv", "custom"]:
            logger.error(f"❌ Invalid platform: {platform_name}")
            return False
            
        if platform_name == self.current_platform:
            logger.info(f"✅ Already on {platform_name} platform")
            return True
            
        logger.info(f"🔄 Switching from {self.current_platform} to {platform_name} platform")
        
        # Close current platform connection
        self.disconnect_current_platform()
        
        # Switch platform
        self.current_platform = platform_name
        
        # Connect to new platform
        if platform_name == "deriv":
            self.start_deriv_connection()
        else:
            self.start_custom_connection()
            
        logger.info(f"✅ Successfully switched to {platform_name} platform")
        return True

    def disconnect_current_platform(self):
        """Disconnect from current platform"""
        if self.current_platform == "deriv" and self.deriv_ws:
            self.deriv_ws.close()
            self.deriv_connected = False
            self.authorized = False
            self.subscribed = False
        elif self.current_platform == "custom":
            self.custom_connected = False

    def start_custom_connection(self):
        """Start connection to custom trading platform"""
        logger.info("🔌 Starting custom platform connection...")
        self.custom_connected = True

# Global trading bot instance
trading_bot = TradingBot()

@app.route('/')
def index():
    return "QuantumTrader Pro Server is running! Use SocketIO for connections."

@socketio.on('connect')
def handle_connect():
    try:
        client_ip = request.remote_addr
        
        with trading_bot.client_lock:
            trading_bot.connected_clients += 1
            
            if client_ip in trading_bot.client_ips:
                trading_bot.client_ips[client_ip] += 1
            else:
                trading_bot.client_ips[client_ip] = 1
        
        logger.info(f"✅ Client connected from {client_ip}. Total clients: {trading_bot.connected_clients}")
        
        emit('connection', {
            'status': 'connected',
            'message': 'Connected to Trading Bot Server',
            'timestamp': datetime.now().isoformat()
        })
        
        emit('trading_status', {
            'enabled': trading_bot.trading_enabled,
            'timestamp': datetime.now().isoformat()
        })
        
        trading_bot.broadcast_system_summary()
        
    except Exception as e:
        logger.error(f"Error in connect handler: {e}")
        return True

@socketio.on('disconnect')
def handle_disconnect():
    try:
        client_ip = request.remote_addr
        
        with trading_bot.client_lock:
            trading_bot.connected_clients = max(0, trading_bot.connected_clients - 1)
            
            if client_ip in trading_bot.client_ips:
                trading_bot.client_ips[client_ip] -= 1
                if trading_bot.client_ips[client_ip] <= 0:
                    del trading_bot.client_ips[client_ip]
        
        logger.info(f"Client disconnected from {client_ip}. Total clients: {trading_bot.connected_clients}")
    except Exception as e:
        logger.error(f"Error in disconnect handler: {e}")

@socketio.on('trading_control')
def handle_trading_control(data):
    try:
        enabled = data.get('enabled', True)
        trading_bot.trading_enabled = enabled
        logger.info(f"Trading {'ENABLED' if enabled else 'DISABLED'}")
        
        emit('trading_status', {
            'enabled': enabled,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error in trading_control handler: {e}")

@socketio.on('switch_platform')
def handle_switch_platform(data):
    try:
        platform_name = data.get('platform')
        if platform_name in ['deriv', 'custom']:
            success = trading_bot.switch_platform(platform_name)
            emit('platform_status', {
                'status': 'success' if success else 'error',
                'platform': platform_name,
                'message': f"Switched to {platform_name} platform" if success else f"Failed to switch to {platform_name}"
            })
            
            trading_bot.broadcast_system_summary()
        else:
            emit('platform_status', {
                'status': 'error',
                'message': 'Invalid platform name. Use "deriv" or "custom"'
            })
    except Exception as e:
        logger.error(f"Platform switch error: {e}")
        emit('platform_status', {
            'status': 'error',
            'message': str(e)
        })

@socketio.on('get_platform_info')
def handle_get_platform_info():
    try:
        platform_info = trading_bot.get_platform_info()
        emit('platform_info', platform_info)
    except Exception as e:
        logger.error(f"Get platform info error: {e}")

@socketio.on('request_data')
def handle_request_data(data):
    try:
        data_type = data.get('data_type')
        if data_type == 'system_summary':
            trading_bot.broadcast_system_summary()
        elif data_type == 'historical_candles':
            candles = []
            base_price = 100.0
            current_time = int(datetime.now().timestamp()) - 3600
            
            for i in range(100):
                open_price = base_price + (i * 0.1)
                close_price = open_price + (0.5 if i % 2 == 0 else -0.3)
                high_price = max(open_price, close_price) + 0.2
                low_price = min(open_price, close_price) - 0.2
                
                candles.append({
                    'time': current_time + (i * 60),
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': 1000
                })
            
            emit('candles', candles)
    except Exception as e:
        logger.error(f"Error in request_data handler: {e}")

@socketio.on('emergency_close_all')
def handle_emergency_close_all():
    try:
        current_price = trading_bot.trading_logic.current_price
        if current_price:
            closed_positions = trading_bot.close_all_open_trades(current_price)
            if closed_positions:
                trading_bot.broadcast_closed_positions(closed_positions)
                trading_bot.broadcast_system_summary()
                logger.info(f"🚨 Emergency close completed: {len(closed_positions)} trades closed")
                return {'status': 'success', 'closed': len(closed_positions), 'message': f'Closed {len(closed_positions)} trades'}
            else:
                return {'status': 'success', 'closed': 0, 'message': 'No open trades to close'}
        return {'status': 'error', 'message': 'No current price available'}
    except Exception as e:
        logger.error(f"Emergency close error: {e}")
        return {'status': 'error', 'message': str(e)}

@socketio.on('get_open_trades_info')
def handle_get_open_trades_info():
    try:
        open_trades_info = []
        current_time = datetime.now()
        
        for position in trading_bot.trading_logic.positions:
            if position.get('status') == 'open':
                time_open = current_time - position['opened_at']
                minutes_open = time_open.total_seconds() / 60
                time_remaining = max(0, 8 - minutes_open)
                
                trade_info = {
                    'id': position['id'],
                    'direction': position['direction'],
                    'strategy': position['strategy'],
                    'entry_price': position['entry_price'],
                    'current_price': trading_bot.trading_logic.current_price,
                    'amount': position['size'],
                    'time_open_minutes': round(minutes_open, 1),
                    'time_remaining_minutes': round(time_remaining, 1),
                    'timestamp': position['opened_at'].isoformat(),
                    'is_near_timeout': time_remaining <= 2,
                    'is_timed_out': time_remaining <= 0
                }
                open_trades_info.append(trade_info)
        
        return {'status': 'success', 'open_trades': open_trades_info}
    except Exception as e:
        logger.error(f"Get open trades info error: {e}")
        return {'status': 'error', 'message': str(e)}

@socketio.on_error()
def error_handler(e):
    logger.error(f"SocketIO error: {e}")

@socketio.on_error_default
def default_error_handler(e):
    logger.error(f"SocketIO default error: {e}")

def run_server():
    logger.info("🚀 Starting QuantumTrader Pro System...")
    logger.info(f"📊 Active Strategies: {', '.join(config.ACTIVE_STRATEGIES)}")
    logger.info(f"💰 Initial Balance: ${config.INITIAL_BALANCE}")
    logger.info(f"⚡ Trading Enabled: {config.TRADING_ENABLED}")
    logger.info(f"🎯 Real Trading: {config.TRADE_EXECUTION}")
    
    # Initialize real trading
    if trading_bot.real_trading_enabled:
        logger.info("💰 REAL TRADING ENABLED - Trades will execute on Deriv platform")
    
    # Start connection monitoring
    trading_bot.start_connection_monitor()
    
    # Start platform connection
    trading_bot.start_deriv_connection()
    
    # Test real trading after delay
    if trading_bot.real_trading_enabled:
        logger.info("🧪 Testing real trading functionality...")
        import time
        time.sleep(8)  # Wait for connection to stabilize
        trading_bot.test_real_trade()
    
    logger.info("Starting WebSocket server on http://0.0.0.0:5000")
    
    try:
        # FIXED: Completely clean socketio.run call
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=5000, 
            debug=False, 
            use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    run_server()
# CRITICAL FIX: Enhanced WebSocket reconnection
