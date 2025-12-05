# bot.py — QUANTUMTRADER PRO v7.4 — FULLY FIXED & SECURED
import eventlet
eventlet.monkey_patch()

import logging
import threading
import time
import json
import websocket
import random
import os
import hmac
import hashlib
from datetime import datetime, date
from typing import List, Dict, Optional

# =========================== LOGGING SETUP ===========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-12s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("trades.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("QUANTUMTRADER")

from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO

import config
from deriv_connection import DerivConnection, ConnectionState
from ai_core import MLTradePredictor, AIStrategyOptimizer
from trade_manager import EnhancedTradingManager
from telegram_notifier import telegram
from strategies import load_strategies, get_strategy
from strategy_debug import debug_aggressive_strategy, get_debug_strategy

# ======================== MT5 BRIDGE (SECURE) ========================
try:
    from mt5_bridge import mt5_bridge
    MT5_BRIDGE_ENABLED = True
    logger.info("MT5 Bridge loaded successfully")
except ImportError as e:
    MT5_BRIDGE_ENABLED = False
    logger.warning(f"MT5 Bridge disabled: {e}")

# Required for HMAC signing
MT5_SECRET_KEY = os.getenv("MT5_SECRET_KEY", config.MT5_SECRET_KEY if hasattr(config, "MT5_SECRET_KEY") else "change-me-securely")

load_strategies()

# ========================= PROJECT ROOT =========================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ========================= FLASK APP ============================
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates")
)
app.config['SECRET_KEY'] = 'quantumtrader-pro-2025-v7.4'

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1_000_000
)

# ========================= GLOBAL STATE =========================
account_balance = config.INITIAL_BALANCE
peak_balance = config.INITIAL_BALANCE
daily_start_balance = config.INITIAL_BALANCE
last_price = 0.0
candles: List[Dict] = []
active_contracts: Dict[str, Dict] = {}
has_forced_trade = False
last_candle_time = 0
MIN_CONFIDENCE = config.MIN_CONFIDENCE

# Trade cooldown & safety
last_trade_time: Dict[str, float] = {}
TRADE_COOLDOWN = 12  # seconds per strategy
MAX_DAILY_LOSS_PCT = 15.0  # Stop trading if down 15% today
TRADING_HALTED = False

# Exit reasons
EXIT_REASONS = {
    "take_profit": "take_profit",
    "stop_loss": "stop_loss",
    "time_expiry": "time_expiry",
    "manual": "manual_close",
    "trailing": "trailing_stop",
    "reversal": "signal_reversal"
}

# ========================= CORE COMPONENTS =========================
ml_predictor = MLTradePredictor()
ai_optimizer = AIStrategyOptimizer(os.getenv("OPENAI_API_KEY", "dummy"))
trading_manager = EnhancedTradingManager(get_strategy_func=get_strategy)
debug_strategy = get_debug_strategy("aggressive")

# ========================= DERIV CONNECTION =========================
deriv_conn = DerivConnection(
    app_id=config.APP_ID,
    token=config.API_TOKEN,
    is_demo=config.IS_DEMO
)

# ======================== DAILY RESET TRACKER ========================
def update_daily_balance():
    global daily_start_balance, peak_balance
    today = date.today()
    if not hasattr(update_daily_balance, "last_date"):
        update_daily_balance.last_date = today
        daily_start_balance = account_balance
        peak_balance = account_balance

    if update_daily_balance.last_date != today:
        update_daily_balance.last_date = today
        daily_start_balance = account_balance
        peak_balance = account_balance
        logger.info("New trading day — daily loss tracker reset")

# ========================= SECURITY: HMAC MT5 ========================
def send_mt5_signal_secure(signal: str, strategy: str, confidence: int):
    if not MT5_BRIDGE_ENABLED or TRADING_HALTED:
        return False

    entry = last_price
    sl_price = round(entry * (1 - 0.005) if signal == "buy" else entry * (1 + 0.005), 5)
    tp_price = round(entry * (1 + 0.010) if signal == "buy" else entry * (1 - 0.010), 5)

    payload = {
        "signal": signal,
        "symbol": config.SYMBOL,
        "price": entry,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "strategy": strategy,
        "confidence": confidence,
        "timestamp": int(time.time())
    }

    message = json.dumps(payload, separators=(',', ':'))
    signature = hmac.new(
        MT5_SECRET_KEY.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    signed_payload = {
        "data": payload,
        "signature": signature
    }

    success = mt5_bridge.write_signal(signed_payload)
    if success:
        logger.info(f"MT5 SIGNAL SECURE → {signal.upper()} | {strategy} | {confidence}%")
    return success

# ========================= SAFETY CHECKS =========================
def check_daily_loss_limit():
    global TRADING_HALTED
    update_daily_balance()
    drawdown = (peak_balance - account_balance) / peak_balance * 100
    if drawdown >= MAX_DAILY_LOSS_PCT and not TRADING_HALTED:
        TRADING_HALTED = True
        logger.critical(f"DAILY LOSS LIMIT EXCEEDED ({drawdown:.1f}%) — TRADING HALTED")
        socketio.emit('system_alert', {
            'type': 'danger',
            'title': 'TRADING HALTED',
            'message': f'Daily loss limit reached ({drawdown:.1f}%). Bot paused for safety.'
        })
        if config.TELEGRAM_ENABLED:
            telegram.notify_error("DAILY LOSS LIMIT", f"Drawdown: {drawdown:.1f}% — Trading halted")

def can_place_trade(strategy: str) -> bool:
    if TRADING_HALTED:
        return False
    if not config.TRADING_ENABLED:
        return False
    now = time.time()
    last = last_trade_time.get(strategy, 0)
    if now - last < TRADE_COOLDOWN:
        return False
    last_trade_time[strategy] = now
    return True

# ========================= TRADE EXECUTION =========================
def place_trade(signal: str, strategy: str = "scalper", confidence: int = 80):
    global has_forced_trade, account_balance, peak_balance

    if not can_place_trade(strategy):
        logger.info(f"Cooldown active for {strategy} — trade blocked")
        return

    confidence = min(confidence, 100)
    allocation = config.CAPITAL_ALLOCATION.get(strategy, 0)
    if allocation <= 0 and strategy not in ["manual", "debug", "demo_init"]:
        logger.warning(f"Strategy {strategy} has 0% allocation — blocked")
        return

    amount = config.MAX_TRADE_AMOUNT
    contract_type = "CALL" if signal.lower() == "buy" else "PUT"

    # Send secure MT5 signal
    send_mt5_signal_secure(signal, strategy, confidence)

    if config.IS_DEMO:
        trade_id = f"demo_{int(time.time())}_{random.randint(1000,9999)}"
        logger.info(f"DEMO TRADE: {contract_type} ${amount} @ {last_price:.5f} | {strategy}")

        socketio.emit('trade_placed', {
            'id': trade_id,
            'type': contract_type,
            'amount': amount,
            'strategy': strategy,
            'confidence': confidence,
            'is_real': False
        })

        # Simulate realistic result
        def simulate_result():
            time.sleep(random.uniform(4, 7))
            win = random.random() < 0.52  # ~52% win rate (realistic)
            profit = amount * 0.75 if win else -amount * 0.95
            global account_balance, peak_balance
            account_balance += profit
            peak_balance = max(peak_balance, account_balance)

            socketio.emit('trade_result', {
                'id': trade_id,
                'profit': round(profit, 2),
                'balance': round(account_balance, 2),
                'success': win,
                'exit_reason': "take_profit" if win else "stop_loss"
            })
            check_daily_loss_limit()

        threading.Thread(target=simulate_result, daemon=True).start()
        return

    # === REAL TRADE ===
    try:
        deriv_conn.place_trade(
            symbol=config.SYMBOL,
            contract_type=contract_type,
            amount=amount,
            duration=5
        )
        has_forced_trade = True
        logger.info(f"REAL TRADE FIRED → {contract_type} ${amount} | {strategy} | {confidence}%")

        if config.TELEGRAM_ENABLED:
            telegram.notify_signal({
                "signal": signal.upper(),
                "price": last_price,
                "strategy": strategy,
                "confidence": confidence
            })

    except Exception as e:
        logger.error(f"TRADE FAILED → {e}")

# ========================= MESSAGE HANDLERS =========================
def handle_deriv_message(data):
    global account_balance, last_price, candles, peak_balance

    try:
        msg_type = data.get("msg_type")

        if msg_type == "balance":
            bal = data["balance"]["balance"]
            new_balance = float(bal)
            if abs(new_balance - account_balance) > 0.01:
                logger.info(f"BALANCE UPDATE: ${account_balance:.2f} → ${new_balance:.2f}")
                account_balance = new_balance
                peak_balance = max(peak_balance, account_balance)
                socketio.emit('balance_update', {'balance': round(account_balance, 2)})
                check_daily_loss_limit()

        elif msg_type == "tick":
            quote = data.get("tick", {}).get("quote")
            if quote:
                last_price = float(quote)
                socketio.emit('price_update', {'price': last_price})

        elif msg_type == "candles":
            cds = data.get("candles")
            if cds:
                candles = cds
                logger.info(f"Received {len(candles)} candles")
                socketio.emit('candles_update', {'count': len(candles), 'candles': candles[-100:]})
                process_market_cycle()

        elif msg_type in ["buy", "proposal_open_contract"]:
            buy = data.get("buy") or data.get("proposal_open_contract")
            if buy and buy.get("contract_id"):
                cid = buy["contract_id"]
                active_contracts[cid] = buy
                socketio.emit('trade_placed', {
                    'id': cid,
                    'type': buy['contract_type'],
                    'amount': buy.get('buy_price', 2.0),
                    'is_real': True
                })

        elif msg_type == "contract_update":
            contract = data.get("contract_update", {})
            if contract.get("is_sold"):
                cid = contract.get("contract_id")
                profit = contract.get("profit", 0)
                is_win = profit > 0

                # Determine real exit reason
                reason = "time_expiry"
                if "sell_spot" in contract and "entry_spot" in contract:
                    entry = float(contract["entry_spot"])
                    exit_p = float(contract["sell_spot"])
                    if is_win:
                        reason = "take_profit" if abs(exit_p - entry) > 0.5 else "time_expiry"
                    else:
                        reason = "stop_loss"

                socketio.emit('trade_result', {
                    'id': cid,
                    'profit': profit,
                    'success': is_win,
                    'exit_reason': reason
                })

                # Balance will be updated via "balance" message — safer
                deriv_conn.get_balance()

    except Exception as e:
        logger.error(f"Message handler error: {e}", exc_info=True)

# ========================= MARKET CYCLE =========================
def process_market_cycle():
    if len(candles) < 20:
        return

    if config.IS_DEMO and not has_forced_trade:
        place_trade("buy", "demo_init", 95)
        return

    result = trading_manager.run_cycle(candles, last_price)
    signal = result.get("signal")
    confidence = min(result.get("confidence", 0), 100)
    strategy = result.get("strategy", "unknown")

    if (signal in ("buy", "sell") and confidence >= MIN_CONFIDENCE and
        config.CAPITAL_ALLOCATION.get(strategy, 0) > 0 and can_place_trade(strategy)):
        place_trade(signal, strategy, confidence)
    else:
        logger.info(f"HOLD | {strategy} | Conf: {confidence}%")

# ========================= SOCKETIO =========================
@socketio.on('connect')
def on_connect():
    enabled = [s for s, a in config.CAPITAL_ALLOCATION.items() if a > 0]
    socketio.emit('system_status', {
        'status': deriv_conn.get_state().value,
        'balance': round(account_balance, 2),
        'mode': 'DEMO' if config.IS_DEMO else 'REAL',
        'price': last_price,
        'enabled_strategies': enabled,
        'mt5_bridge': MT5_BRIDGE_ENABLED,
        'halted': TRADING_HALTED
    })

@socketio.on('manual_trade')
def manual_trade(data):
    signal = data.get('signal', 'buy')
    if signal in ['buy', 'sell']:
        place_trade(signal, "manual", 100)

@socketio.on('test_mt5_signal')
def test_mt5():
    if send_mt5_signal_secure("buy", "test", 95):
        socketio.emit('system_status', {'message': 'MT5 Test Signal Sent'})
    else:
        socketio.emit('system_status', {'message': 'MT5 Bridge Failed'})

# ========================= STARTUP =========================
def initialize_bot():
    print("\n" + "="*64)
    print("   QUANTUMTRADER PRO v7.4 — FULLY SECURE & FIXED")
    print("   Professional Deriv.com + MT5 Hybrid Trading Bot")
    print(f"   Mode: {'DEMO' if config.IS_DEMO else 'REAL'} | Trading: {'ON' if config.TRADING_ENABLED else 'OFF'}")
    print(f"   Daily Loss Limit: {MAX_DAILY_LOSS_PCT}% | Cooldown: {TRADE_COOLDOWN}s")
    print(f"   MT5 Bridge: {'ENABLED' if MT5_BRIDGE_ENABLED else 'DISABLED'}")
    print("="*64 + "\n")

    deriv_conn.add_message_handler(handle_deriv_message)
    deriv_conn.connect()

    if config.IS_DEMO:
        threading.Thread(target=lambda: (time.sleep(3), simulate_demo_data()), daemon=True).start()

def simulate_demo_data():
    global candles, last_price
    time.sleep(3)
    base = 100.0
    price = base
    candles = []
    for i in range(100):
        change = random.uniform(-0.4, 0.4)
        price += change
        candles.append({
            "open": price,
            "high": price + random.uniform(0, 0.3),
            "low": price - random.uniform(0, 0.3),
            "close": price,
            "epoch": int(time.time()) - (100 - i) * 60
        })
    last_price = price
    socketio.emit('candles_update', {'count': 100, 'candles': candles[-100:]})
    socketio.emit('price_update', {'price': last_price})

if __name__ == '__main__':
    initialize_bot()
    socketio.run(app, host=config.HOST, port=config.PORT, debug=False, use_reloader=False)