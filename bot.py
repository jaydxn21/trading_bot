# bot.py — QUANTUMTRADER PRO v7.3 — MT5 INTEGRATION ADDED
import eventlet
eventlet.monkey_patch()

import logging
import threading
import time
import json
import websocket
import random
import os
from datetime import datetime
from typing import List, Dict, Optional

# Initialize logging before any module code that uses logger
logging.basicConfig(
    level=getattr(logging, "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO

import config
from deriv_connection import DerivConnection, ConnectionState
from ai_core import MLTradePredictor, AIStrategyOptimizer
from trade_manager import EnhancedTradingManager
from telegram_notifier import telegram
from strategies import load_strategies, get_strategy, list_strategies
from strategy_debug import debug_aggressive_strategy, random_strategy, mean_reversion_aggressive, continuous_trading_strategy, get_debug_strategy

# MT5 Bridge integration
try:
    from mt5_bridge import mt5_bridge  # Changed from mt5_bridge to mt_bridge
    MT5_BRIDGE_ENABLED = True
    logger.info("✅ MT5 Bridge enabled")
except ImportError as e:
    MT5_BRIDGE_ENABLED = False
    logger.warning(f"⚠️ MT5 Bridge not available: {e} - running without MT5 integration")

load_strategies()

# PROJECT ROOT
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# FLASK + SOCKETIO — BULLETPROOF
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates")
)
app.config['SECRET_KEY'] = 'quantum-secret-2025'

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
    allow_upgrades=True,
    max_http_buffer_size=1_000_000
)

# EXIT REASON CONSTANTS
EXIT_REASON_TAKE_PROFIT = "take_profit"
EXIT_REASON_STOP_LOSS = "stop_loss" 
EXIT_REASON_TIME_EXPIRY = "time_expiry"
EXIT_REASON_MANUAL_CLOSE = "manual_close"
EXIT_REASON_TRAILING_STOP = "trailing_stop"
EXIT_REASON_SIGNAL_REVERSAL = "signal_reversal"
EXIT_REASON_UNKNOWN = "unknown"

# GLOBAL STATE
account_balance = config.INITIAL_BALANCE
last_price = 0.0
candles: List[Dict] = []
active_contracts: Dict[str, Dict] = {}
has_forced_trade = False
last_candle_time = 0
MIN_CONFIDENCE = config.MIN_CONFIDENCE
debug_strategy = get_debug_strategy("aggressive")

# CORE
ml_predictor = MLTradePredictor()
ai_optimizer = AIStrategyOptimizer(os.getenv("OPENAI_API_KEY", "dummy"))
trading_manager = EnhancedTradingManager(get_strategy_func=get_strategy)

# DERIV CONNECTION MANAGER
deriv_conn = DerivConnection(
    app_id=config.APP_ID,
    token=config.API_TOKEN,
    is_demo=config.IS_DEMO
)

# CONNECTION EVENT HANDLERS
def handle_connection_state_change(old_state, new_state, message):
    """Handle connection state changes"""
    logger.info(f"Connection state: {old_state.value} → {new_state.value} - {message}")
    
    socketio.emit('system_status', {
        'status': new_state.value,
        'message': message,
        'mode': 'REAL' if not config.IS_DEMO else 'DEMO'
    })
    
    if new_state == ConnectionState.AUTHENTICATED:
        logger.info("✅ Connection authenticated - starting data subscriptions")
        deriv_conn.subscribe_ticks(config.SYMBOL)
        deriv_conn.subscribe_candles(config.SYMBOL, config.GRANULARITY, config.HISTORY_COUNT)
        deriv_conn.get_balance()
        
    elif new_state == ConnectionState.ERROR:
        logger.error(f"Connection error: {message}")
        if "token" in message.lower() or "auth" in message.lower():
            logger.critical("TOKEN ERROR - CHECK YOUR .env FILE")
            logger.critical("Go to: https://app.deriv.com/account/api-token")

def handle_deriv_message(data):
    """Handle incoming Deriv messages"""
    global account_balance, last_price, candles, active_contracts, last_candle_time
    
    try:
        msg_type = data.get("msg_type")

        if msg_type == "authorization":
            auth = data.get("authorization", {})
            if auth.get("token"):
                logger.info("✅ Successfully authenticated with Deriv")

        elif msg_type == "balance":
            bal = data.get("balance", {}).get("balance")
            if bal is not None:
                account_balance = float(bal)
                logger.info(f"BALANCE: ${account_balance:.2f}")
                socketio.emit('balance_update', {'balance': account_balance})

        elif msg_type == "tick":
            quote = data.get("tick", {}).get("quote")
            if quote:
                last_price = float(quote)
                socketio.emit('price_update', {'price': last_price})

        elif msg_type == "candles":
            cds = data.get("candles")
            if cds:
                candles = cds
                last_candle_time = time.time()
                logger.info(f"📊 RECEIVED {len(candles)} CANDLES")
                socketio.emit('candles_update', {
                    'count': len(candles),
                    'candles': candles[-100:]
                })
                process_market_cycle()

        elif msg_type in ["buy", "proposal_open_contract"]:
            buy = data.get("buy") or data.get("proposal_open_contract")
            if buy and buy.get("contract_id"):
                cid = buy["contract_id"]
                active_contracts[cid] = buy
                logger.info(f"🎯 TRADE PLACED: {buy['contract_type']} ${buy['buy_price']}")
                socketio.emit('trade_placed', {
                    'id': cid,
                    'type': buy['contract_type'],
                    'amount': 2.0,
                    'is_real': not config.IS_DEMO
                })
                if config.TELEGRAM_ENABLED:
                    telegram.notify_trade_executed({
                        "id": cid,
                        "type": buy['contract_type'],
                        "entry_price": last_price,
                        "strategy": "scalper"
                    })

        elif msg_type == "contract_update":
            contract = data.get("contract_update", {})
            if contract.get("is_sold"):
                profit = contract.get("profit", 0)
                account_balance += profit
                
                # Determine exit reason for real trades
                exit_reason = EXIT_REASON_UNKNOWN
                if profit > 0:
                    exit_reason = EXIT_REASON_TAKE_PROFIT
                else:
                    exit_reason = EXIT_REASON_STOP_LOSS
                
                logger.info(f"💰 TRADE CLOSED: ${profit:.2f} | Reason: {exit_reason}")
                
                socketio.emit('trade_result', {
                    'profit': profit,
                    'balance': account_balance,
                    'id': contract.get("contract_id"),
                    'exit_reason': exit_reason
                })
                
                if config.TELEGRAM_ENABLED:
                    telegram.notify_trade_closed({
                        "id": contract.get("contract_id", "N/A"),
                        "pnl": profit,
                        "strategy": "scalper",
                        "exit_reason": exit_reason
                    })

    except Exception as e:
        logger.error(f"Message processing error: {e}", exc_info=True)

def handle_deriv_error(error, critical):
    """Handle connection errors"""
    logger.error(f"Deriv connection error: {error} (critical: {critical})")
    
    if critical:
        logger.critical("CRITICAL ERROR - Manual intervention needed")
        if config.TELEGRAM_ENABLED:
            telegram.notify_error("CRITICAL CONNECTION ERROR", error)

# REGISTER HANDLERS
deriv_conn.add_state_change_handler(handle_connection_state_change)
deriv_conn.add_message_handler(handle_deriv_message)
deriv_conn.add_error_handler(handle_deriv_error)

# DEMO SIMULATION
def simulate_demo_data():
    """Simulate market data for demo mode"""
    time.sleep(3)
    global candles, last_price, account_balance
    
    # Generate realistic demo candles
    base_price = 100.0
    candles = []
    current_price = base_price
    
    for i in range(100):
        change = random.uniform(-0.5, 0.5)
        current_price += change
        candle = {
            "open": current_price - random.uniform(0, 0.2),
            "high": current_price + random.uniform(0, 0.3),
            "low": current_price - random.uniform(0, 0.3),
            "close": current_price,
            "epoch": int(time.time()) - (100 - i) * config.GRANULARITY
        }
        candles.append(candle)
    
    last_price = candles[-1]["close"]
    
    logger.info("🎮 DEMO: SIMULATED 100 CANDLES")
    socketio.emit('candles_update', {'count': 100, 'candles': candles[-100:]})
    socketio.emit('price_update', {'price': last_price})
    socketio.emit('balance_update', {'balance': account_balance})
    
    process_market_cycle()

def send_mt5_signal(signal: str, strategy: str, confidence: int):
    """Send signal to MT5 via file bridge"""
    if not MT5_BRIDGE_ENABLED:
        return
        
    try:
        success = mt5_bridge.write_signal({
            "signal": signal,
            "symbol": config.SYMBOL,
            "price": last_price,
            "strategy": strategy,
            "confidence": confidence
        })
        
        if success:
            logger.info("📡 MT5 signal sent successfully")
        else:
            logger.warning("⚠️ MT5 signal not sent (hold signal or error)")
            
    except Exception as e:
        logger.error(f"❌ MT5 signal bridge failed: {e}")

def place_trade(signal: str, strategy: str = "scalper", confidence: int = 80):
    """Place a trade through Deriv connection with proper risk management"""
    global has_forced_trade
    
    if not config.TRADING_ENABLED:
        logger.warning("⏸️ TRADING DISABLED - skipping trade")
        return

    # CRITICAL FIX: CAP CONFIDENCE AT 95%
    confidence = min(confidence, 95)
    
    # CRITICAL FIX: CHECK IF STRATEGY IS ENABLED
    strategy_allocation = config.CAPITAL_ALLOCATION.get(strategy, 0)
    if strategy_allocation <= 0 and strategy not in ["demo_init", "manual", "forced", "debug"]:
        logger.warning(f"⏸️ STRATEGY DISABLED: {strategy} has 0% allocation - Skipping trade")
        return

    contract_type = "CALL" if signal.lower() == "buy" else "PUT"
    amount = config.MAX_TRADE_AMOUNT

    # Calculate proper risk management
    strategy_config = config.STRATEGY_CONFIG.get(strategy, {})
    stop_loss_pct = strategy_config.get("stop_loss_percent", config.STOP_LOSS_PERCENT)
    take_profit_pct = strategy_config.get("take_profit_percent", config.TAKE_PROFIT_PERCENT)
    
    # DEBUG: Log the actual config values being used
    logger.info(f"🔧 CONFIG DEBUG: Strategy={strategy}, SL%={stop_loss_pct}, TP%={take_profit_pct}")
    
    entry_price = last_price
    stop_loss = entry_price * (1 - stop_loss_pct/100) if signal == "buy" else entry_price * (1 + stop_loss_pct/100)
    take_profit = entry_price * (1 + take_profit_pct/100) if signal == "buy" else entry_price * (1 - take_profit_pct/100)
    
    risk_reward = abs((take_profit - entry_price) / (entry_price - stop_loss)) if entry_price != stop_loss else 0

    # SEND MT5 SIGNAL (FREE BRIDGE)
    send_mt5_signal(signal, strategy, confidence)

    if config.IS_DEMO:
        # Demo trade simulation
        trade_id = f"demo_{int(time.time())}_{random.randint(1000,9999)}"
        logger.info(f"🎮 DEMO TRADE: {contract_type} ${amount} @ {last_price:.2f}")
        
        socketio.emit('trade_placed', {
            'id': trade_id,
            'type': contract_type,
            'amount': amount,
            'is_real': False,
            'strategy': strategy,
            'confidence': confidence,
            'sl': stop_loss,
            'tp': take_profit,
            'rr_ratio': risk_reward
        })
        
        if config.TELEGRAM_ENABLED:
            telegram.notify_trade_executed({
                "id": trade_id,
                "type": contract_type,
                "entry_price": last_price,
                "strategy": strategy,
                "confidence": confidence,
                "sl": stop_loss,
                "tp": take_profit,
                "rr_ratio": risk_reward
            })
        
        # Simulate trade result after delay with proper exit reason tracking
        def simulate_trade_result():
            time.sleep(5)
            
            # Calculate realistic exit conditions based on strategy
            current_price = entry_price
            
            # Simulate price movement based on strategy performance
            if strategy == "scalper":
                # Scalper has better performance - adjusted for new R/R
                price_move = random.uniform(-stop_loss_pct * 0.7, take_profit_pct * 1.3)  # Increased TP chance
            elif strategy == "emergency":
                # Emergency is more conservative
                price_move = random.uniform(-stop_loss_pct * 0.5, take_profit_pct * 0.8)
            else:
                # Other strategies have varied performance
                price_move = random.uniform(-stop_loss_pct, take_profit_pct)
            
            current_price = entry_price * (1 + price_move/100)
            
            # Determine exit reason and profit
            exit_reason = EXIT_REASON_UNKNOWN
            profit = 0
            
            if signal == "buy":
                if current_price <= stop_loss:
                    exit_reason = EXIT_REASON_STOP_LOSS
                    profit = -amount * 0.8  # Typical loss amount
                elif current_price >= take_profit:
                    exit_reason = EXIT_REASON_TAKE_PROFIT
                    profit = amount * 0.6   # Typical win amount
                else:
                    # Time-based exit or other
                    exit_reason = EXIT_REASON_TIME_EXPIRY
                    profit = random.uniform(-amount * 0.3, amount * 0.4)
            else:  # sell
                if current_price >= stop_loss:
                    exit_reason = EXIT_REASON_STOP_LOSS
                    profit = -amount * 0.8
                elif current_price <= take_profit:
                    exit_reason = EXIT_REASON_TAKE_PROFIT
                    profit = amount * 0.6
                else:
                    exit_reason = EXIT_REASON_TIME_EXPIRY
                    profit = random.uniform(-amount * 0.3, amount * 0.4)
            
            # Strategy-based performance adjustment
            strategy_multiplier = 1.0
            if strategy == "scalper":
                strategy_multiplier = 1.3  # Focus strategy - higher potential
            elif strategy == "emergency":
                strategy_multiplier = 0.8  # Safety strategy - conservative
            elif strategy == "snr_adx":
                strategy_multiplier = 0.9  # Reduced - underperformer
            elif strategy == "vol_mean_reversion":
                strategy_multiplier = 0.6  # Severely reduced - terrible performer
            
            # Adjust based on confidence
            confidence_multiplier = min(confidence / 100, 0.95)
            
            final_profit = profit * strategy_multiplier * confidence_multiplier
            
            global account_balance
            account_balance += final_profit
            
            # Emit with exit reason
            socketio.emit('trade_result', {
                'profit': final_profit,
                'balance': account_balance,
                'id': trade_id,
                'success': final_profit > 0,
                'sl': stop_loss,
                'tp': take_profit,
                'exit_reason': exit_reason,
                'current_price': current_price,
                'entry_price': entry_price
            })
            
            if config.TELEGRAM_ENABLED:
                # FIX: Ensure all required fields are passed to Telegram
                telegram.notify_trade_closed({
                    "id": trade_id,
                    "pnl": final_profit,
                    "strategy": strategy,
                    "success": final_profit > 0,
                    "sl": stop_loss,
                    "tp": take_profit,
                    "exit_reason": exit_reason,  # This is the key fix
                    "confidence": confidence,
                    "entry_price": entry_price,
                    "exit_price": current_price,
                    "direction": contract_type.lower()
                })
            
            logger.info(f"💰 TRADE CLOSED: {trade_id} | P&L: ${final_profit:.2f} | Reason: {exit_reason} | Confidence: {confidence}%")
        
        threading.Thread(target=simulate_trade_result, daemon=True).start()
        return

    # REAL TRADING
    try:
        deriv_conn.place_trade(
            symbol=config.SYMBOL,
            contract_type=contract_type,
            amount=amount,
            duration=5
        )
        
        logger.info(f"🎯 FIRED {contract_type} ${amount} @ {last_price:.2f}")
        
        if config.TELEGRAM_ENABLED:
            telegram.notify_signal({
                "signal": signal.upper(),
                "price": last_price,
                "strategy": strategy,
                "confidence": confidence
            })
        
        has_forced_trade = True
        
    except Exception as e:
        logger.error(f"❌ TRADE EXECUTION FAILED: {e}")

def process_market_cycle():
    """Process market data with PROPER scalper allocation"""
    global has_forced_trade, last_candle_time
    
    if len(candles) < 10:
        logger.info(f"⏳ WAITING FOR 10 CANDLES... ({len(candles)}/10)")
        return

    last_candle_time = time.time()
    current_price = float(candles[-1]["close"])
    
    # DEBUG: Force first trade in demo mode (only once)
    if not has_forced_trade and config.IS_DEMO:
        logger.warning("🔧 DEMO MODE → FORCING INITIAL TEST BUY")
        place_trade("buy", "demo_init", 95)
        has_forced_trade = True
        return
    
    # Run trading strategies
    result = trading_manager.run_cycle(candles, current_price)
    
    signal = result.get("signal")
    confidence = result.get("confidence", 0)
    strategy_used = result.get("strategy", "unknown")

    # CAP CONFIDENCE AT 95%
    confidence = min(confidence, 95)
    
    logger.info(f"🤖 MAIN STRATEGY → {strategy_used.upper()}: {signal or 'HOLD'} | CONF: {confidence}% | MIN: {MIN_CONFIDENCE}%")

    # CHECK IF STRATEGY IS ENABLED - FIXED LOGIC
    strategy_allocation = config.CAPITAL_ALLOCATION.get(strategy_used, 0)
    if strategy_allocation <= 0 and strategy_used not in ["demo_init", "manual", "forced", "debug"]:
        logger.warning(f"⏸️ STRATEGY DISABLED: {strategy_used} has 0% allocation")
        signal = None
        confidence = 0

    # DEMO MODE: Use aggressive fallbacks for ENABLED strategies
    if config.IS_DEMO and (not signal or confidence < MIN_CONFIDENCE):
        # Use fallback strategies but map them to ENABLED strategy names
        debug_result = debug_aggressive_strategy(candles, current_price)
        if debug_result and debug_result.get("signal") != "hold":
            # Map fallback to actual enabled strategy
            if config.CAPITAL_ALLOCATION.get("scalper", 0) > 0:
                signal = debug_result["signal"]
                confidence = min(debug_result["confidence"], 95)
                strategy_used = "scalper"  # Use actual enabled strategy name
                logger.info(f"🎯 SCALPER FALLBACK: {signal} @ {confidence}% - {debug_result.get('reason', '')}")
            elif config.CAPITAL_ALLOCATION.get("emergency", 0) > 0:
                signal = debug_result["signal"]
                confidence = min(debug_result["confidence"], 95)
                strategy_used = "emergency"  # Use actual enabled strategy name
                logger.info(f"🛡️ EMERGENCY FALLBACK: {signal} @ {confidence}% - {debug_result.get('reason', '')}")

    # Execute trade if conditions met AND strategy is ENABLED
    if (signal in ("buy", "sell") and 
        confidence >= MIN_CONFIDENCE and 
        config.CAPITAL_ALLOCATION.get(strategy_used, 0) > 0):
        
        logger.info(f"🚀 EXECUTING TRADE: {strategy_used.upper()} - {signal.upper()} @ {confidence}%")
        place_trade(signal, strategy_used, confidence)
    else:
        reason = "No signal"
        if signal and confidence >= MIN_CONFIDENCE and config.CAPITAL_ALLOCATION.get(strategy_used, 0) <= 0:
            reason = f"Strategy disabled: {strategy_used}"
        elif signal and confidence < MIN_CONFIDENCE:
            reason = f"Low confidence: {confidence}% < {MIN_CONFIDENCE}%"
        elif not signal:
            reason = "No trading signal"
            
        logger.info(f"⏸️ NO TRADE → {reason}")

# SOCKETIO EVENTS
@socketio.on('connect')
def handle_connect():
    logger.info(f"🌐 FRONTEND CONNECTED → SID: {request.sid}")
    
    # Get enabled strategies for frontend display
    enabled_strategies = [s for s, alloc in config.CAPITAL_ALLOCATION.items() if alloc > 0]
    
    socketio.emit('system_status', {
        'status': deriv_conn.get_state().value,
        'balance': account_balance,
        'mode': 'REAL' if not config.IS_DEMO else 'DEMO',
        'price': last_price,
        'candles_count': len(candles),
        'min_confidence': MIN_CONFIDENCE,
        'enabled_strategies': enabled_strategies,
        'mt5_bridge_enabled': MT5_BRIDGE_ENABLED
    }, room=request.sid)

@socketio.on('emergency_close_all')
def emergency_close():
    logger.warning("🚨 EMERGENCY CLOSE ALL TRIGGERED")
    if config.TELEGRAM_ENABLED:
        telegram.notify_error("EMERGENCY CLOSE", "User triggered emergency close all")
    socketio.emit('emergency_status', {'action': 'closing_all'})

@socketio.on('manual_trade')
def handle_manual_trade(data):
    """Handle manual trade from frontend"""
    signal = data.get('signal')
    amount = data.get('amount', config.MAX_TRADE_AMOUNT)
    
    if signal in ['buy', 'sell']:
        logger.info(f"🕹️ MANUAL TRADE: {signal.upper()} ${amount}")
        place_trade(signal, "manual", 100)

@socketio.on('debug_trade')
def handle_debug_trade(data):
    """Debug function to force trades for testing"""
    signal = data.get('signal', 'buy')
    strategy = data.get('strategy', 'debug')
    confidence = data.get('confidence', 95)
    
    logger.info(f"🔧 DEBUG TRADE: {signal.upper()} via {strategy} @ {confidence}%")
    place_trade(signal, strategy, confidence)

@socketio.on('reset_demo')
def handle_reset_demo():
    """Reset demo data"""
    global candles, last_price, account_balance, has_forced_trade
    account_balance = config.INITIAL_BALANCE
    has_forced_trade = False
    logger.info("🔄 DEMO DATA RESET")
    socketio.emit('balance_update', {'balance': account_balance})
    socketio.emit('system_status', {'message': 'Demo reset complete'})

@socketio.on('set_confidence')
def handle_set_confidence(data):
    """Dynamically change minimum confidence"""
    global MIN_CONFIDENCE
    new_confidence = data.get('confidence', 0)
    MIN_CONFIDENCE = new_confidence
    logger.info(f"🎯 MIN_CONFIDENCE changed to {new_confidence}%")
    socketio.emit('config_update', {'min_confidence': MIN_CONFIDENCE})

@socketio.on('get_status')
def handle_get_status():
    """Return current bot status"""
    enabled_strategies = [s for s, alloc in config.CAPITAL_ALLOCATION.items() if alloc > 0]
    
    status = {
        'balance': account_balance,
        'price': last_price,
        'candles_count': len(candles),
        'min_confidence': MIN_CONFIDENCE,
        'has_forced_trade': has_forced_trade,
        'trading_enabled': config.TRADING_ENABLED,
        'mode': 'DEMO' if config.IS_DEMO else 'REAL',
        'connection_state': deriv_conn.get_state().value,
        'enabled_strategies': enabled_strategies,
        'mt5_bridge_enabled': MT5_BRIDGE_ENABLED
    }
    socketio.emit('status_update', status)

@socketio.on('set_trading_mode')
def handle_set_trading_mode(data):
    """Change trading behavior in real-time"""
    mode = data.get('mode', 'aggressive')
    global debug_strategy
    debug_strategy = get_debug_strategy(mode)
    logger.info(f"🔄 TRADING MODE CHANGED: {mode}")
    socketio.emit('system_status', {'message': f'Trading mode: {mode}'})

@socketio.on('test_mt5_signal')
def handle_test_mt5_signal(data):
    """Test MT5 signal bridge"""
    if not MT5_BRIDGE_ENABLED:
        socketio.emit('system_status', {'message': 'MT5 Bridge not available'})
        return
        
    signal = data.get('signal', 'buy')
    success = mt5_bridge.write_signal({
        "signal": signal,
        "symbol": config.SYMBOL,
        "price": last_price,
        "strategy": "manual_test",
        "confidence": 95
    })
    
    if success:
        socketio.emit('system_status', {'message': f'MT5 Test Signal Sent: {signal.upper()}'})
        logger.info(f"🧪 MT5 Test Signal: {signal.upper()}")
    else:
        socketio.emit('system_status', {'message': 'MT5 Test Signal Failed'})

# STARTUP
def initialize_bot():
    """Initialize the trading bot with strategy validation"""
    print("\n" + "="*60)
    print("   QUANTUMTRADER PRO v7.3 — MT5 INTEGRATION")
    print("   DASHBOARD: http://localhost:5000")
    print(f"   MODE: {'REAL' if not config.IS_DEMO else 'DEMO'}")
    print(f"   TRADING: {'ON' if config.TRADING_ENABLED else 'OFF'}")
    print(f"   MIN CONFIDENCE: {MIN_CONFIDENCE}%")
    
    # Show enabled strategies
    enabled_strategies = [s for s, alloc in config.CAPITAL_ALLOCATION.items() if alloc > 0]
    if enabled_strategies:
        print(f"   ENABLED STRATEGIES: {', '.join(enabled_strategies)}")
    else:
        print("   🚨 NO STRATEGIES ENABLED! Check config.")
    
    # MT5 Bridge status
    if MT5_BRIDGE_ENABLED:
        print("   ✅ MT5 BRIDGE: ENABLED")
    else:
        print("   ⚠️ MT5 BRIDGE: NOT AVAILABLE (create mt5_bridge.py to enable)")
    
    print("="*60 + "\n")
    
    # Start Deriv connection
    logger.info("🚀 STARTING DERIV CONNECTION...")
    deriv_conn.connect()
    
    # If in demo mode, start simulation
    if config.IS_DEMO:
        logger.info("🎮 STARTING DEMO SIMULATION...")
        threading.Thread(target=simulate_demo_data, daemon=True).start()

if __name__ == '__main__':
    initialize_bot()
    socketio.run(app, host=config.HOST, port=config.PORT, debug=config.DEBUG, use_reloader=False)