# bot.py - Main server file with proper datetime serialization

import json
import websocket
import threading
import time
from flask import Flask
from flask_socketio import SocketIO, emit
from datetime import datetime

# Import modular components
from config import *
from trading_logic import TradingLogic
from scalper import ScalperStrategy

# Create a custom JSON module that handles datetime objects
class DateTimeJSON:
    @staticmethod
    def dumps(obj, **kwargs):
        def default_serializer(o):
            if isinstance(o, datetime):
                return o.isoformat()
            raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")
        return json.dumps(obj, default=default_serializer, **kwargs)
    
    @staticmethod
    def loads(s, **kwargs):
        return json.loads(s, **kwargs)

# ───────── Flask + SocketIO ─────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', json=DateTimeJSON)

# Initialize trading strategy
if ACTIVE_STRATEGY == "scalper":
    trading_strategy = ScalperStrategy(INITIAL_BALANCE, RISK_PER_TRADE)
else:
    trading_strategy = TradingLogic(INITIAL_BALANCE, RISK_PER_TRADE)

candles = []
current_candle = None
ws_connection = None
is_authorized = False

# ───────── WebSocket callbacks ─────────
def on_open(ws):
    global ws_connection
    ws_connection = ws
    print("[DerivWS] Connected")
    ws.send(json.dumps({"authorize": API_TOKEN}))

def on_message(ws, message):
    global candles, current_candle, is_authorized
    data = json.loads(message)
    print(f"Received message type: {data.get('msg_type')}")
    
    # Handle authorization response
    if data.get("msg_type") == "authorize":
        is_authorized = True
        print("[DerivWS] Authorized successfully")
        ws.send(json.dumps({
            "ticks_history": SYMBOL,
            "adjust_start_time": 1,
            "count": HISTORY_COUNT,
            "end": "latest",
            "start": 1,
            "style": "candles",
            "granularity": GRANULARITY
        }))
    
    # Historical candles response
    elif data.get("msg_type") == "candles" and "candles" in data:
        candles = data["candles"]
        print(f"[DerivWS] Received {len(candles)} historical candles")
        
        if candles:
            current_candle = candles[-1].copy()
            print(f"Current candle set to epoch: {current_candle.get('epoch', 'N/A')}")
        
        formatted_candles = format_candles(candles)
        socketio.emit("candles", formatted_candles)
        
        ws.send(json.dumps({
            "ticks": SYMBOL,
            "subscribe": 1
        }))
    
    # Live ticks for candle updates
    elif data.get("msg_type") == "tick":
        tick = data["tick"]
        print(f"Received tick: {tick['epoch']} - {tick['quote']}")
        process_tick(tick)

def process_tick(tick):
    global candles, current_candle
    
    epoch = tick["epoch"]
    price = float(tick["quote"])
    
    # Calculate the candle time for this tick
    candle_time = epoch - (epoch % GRANULARITY)
    
    print(f"🕒 Tick: {epoch}, Price: {price}, Candle Time: {candle_time}")
    
    # Candle management
    if current_candle is None:
        current_candle = create_new_candle(candle_time, price)
        candles.append(current_candle)
        print(f"🆕 Created new candle at {candle_time}")
    elif candle_time > current_candle["epoch"]:
        print(f"🎯 CANDLE COMPLETE - Running analysis!")
        
        # Run trading analysis on completed candle (ALWAYS run analysis)
        analysis = trading_strategy.analyze_market(candles, current_candle.get("close", price))
        analysis["timestamp"] = int(time.time())
        
        # Emit analysis to frontend (even if trading is disabled)
        socketio.emit("trading_signal", analysis)
        print(f"📢 EMITTED SIGNAL: {analysis.get('signal', 'wait').upper()}")
        print(f"   Reason: {analysis.get('reason', 'No reason')}")
        print(f"   Confidence: {analysis.get('confidence', 0):.1f}%")
        
        # Execute trade only if enabled and signal is valid
        if TRADING_ENABLED and analysis.get("signal") in ["buy", "sell"]:
            trade = trading_strategy.execute_trade(analysis, price)
            if trade:
                # Ensure trade data is serializable
                trade_serializable = {
                    "id": trade["id"],
                    "direction": trade["direction"],
                    "entry_price": trade["entry_price"],
                    "size": trade["size"],
                    "amount": trade["amount"],
                    "timestamp": trade["timestamp"],
                    "signal_reason": trade["signal_reason"],
                    "confidence": trade["confidence"],
                    "status": trade["status"],
                    "demo": trade["demo"]
                }
                socketio.emit("trade_executed", trade_serializable)
                print(f"💼 TRADE EXECUTED: {trade}")
        
        # Manage open positions with new price
        closed_positions = trading_strategy.manage_open_positions(price)
        for closed in closed_positions:
            # Ensure all data is JSON serializable
            closed_serializable = {
                "id": closed["id"],
                "reason": closed["reason"],
                "pnl": closed["pnl"],
                "pnl_pct": closed["pnl_pct"]
            }
            socketio.emit("trade_closed", closed_serializable)
        
        # Send updated trade history after closing positions
        emit_trade_history()
        
        current_candle = create_new_candle(candle_time, price)
        candles.append(current_candle)
        print(f"🆕 Created new candle at {candle_time}")
        
        if len(candles) > HISTORY_COUNT:
            candles.pop(0)
    else:
        update_current_candle(current_candle, price)
    
    # Emit candle updates
    socketio.emit("candle_update", {
        "time": current_candle["epoch"],
        "open": float(current_candle["open"]),
        "high": float(current_candle["high"]),
        "low": float(current_candle["low"]),
        "close": float(current_candle["close"])
    })
    
    # Emit REAL-TIME balance updates (ensure serializable)
    emit_account_update(price)

def emit_account_update(current_price):
    """Emit account update with serializable data"""
    account_summary = trading_strategy.get_account_summary(current_price)
    # Ensure everything is serializable
    serializable_summary = {
        "balance": account_summary["balance"],
        "equity": account_summary["equity"],
        "open_positions": account_summary["open_positions"],
        "total_trades": account_summary["total_trades"],
        "demo_mode": account_summary["demo_mode"],
        "risk_level": account_summary["risk_level"],
        "consecutive_losses": account_summary["consecutive_losses"],
        "trading_halted": account_summary["trading_halted"],
        "halt_reason": account_summary["halt_reason"],
        "daily_stats": account_summary["daily_stats"]  # This should be serializable
    }
    socketio.emit("account_update", serializable_summary)

def emit_trade_history():
    """Emit trade history with serializable data"""
    # Ensure all trade history entries are serializable
    serializable_history = []
    for trade in trading_strategy.trade_history:
        serializable_trade = {
            "id": trade.get("id"),
            "direction": trade.get("direction"),
            "entry_price": trade.get("entry_price"),
            "exit_price": trade.get("exit_price"),
            "size": trade.get("size"),
            "amount": trade.get("amount"),
            "timestamp": trade.get("timestamp"),
            "profit_loss": trade.get("profit_loss"),
            "status": trade.get("status"),
            "demo": trade.get("demo"),
            "signal_reason": trade.get("signal_reason"),
            "confidence": trade.get("confidence")
        }
        serializable_history.append(serializable_trade)
    socketio.emit("trade_history_update", serializable_history)

def create_new_candle(time, price):
    return {
        "epoch": time,
        "open": price,
        "high": price,
        "low": price,
        "close": price
    }

def update_current_candle(candle, price):
    candle["close"] = price
    if price > candle["high"]:
        candle["high"] = price
    if price < candle["low"]:
        candle["low"] = price

def format_candles(candles_data):
    formatted = []
    for candle in candles_data:
        formatted.append({
            "time": candle.get("epoch", 0),
            "open": float(candle.get("open", 0)),
            "high": float(candle.get("high", 0)),
            "low": float(candle.get("low", 0)),
            "close": float(candle.get("close", 0))
        })
    return formatted

def on_error(ws, error):
    print("[DerivWS] ERROR:", error)

def on_close(ws, close_status_code, close_msg):
    print(f"[DerivWS] Connection closed: {close_status_code} - {close_msg}")
    # Try to reconnect after 5 seconds
    time.sleep(5)
    print("Attempting to reconnect...")
    start_ws()

def start_ws():
    global is_authorized
    is_authorized = False
    ws = websocket.WebSocketApp(
        f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()

# ───────── SocketIO events ─────────
@socketio.on("connect")
def handle_connect():
    print(">> Client connected")
    if candles:
        emit("candles", format_candles(candles))
    
    # Send current price for account summary
    current_price = current_candle["close"] if current_candle else 0
    
    emit("trading_status", {
        "enabled": TRADING_ENABLED,
        "strategy": ACTIVE_STRATEGY,
        "balance": trading_strategy.balance,
        "equity": trading_strategy.equity,
        "demo_mode": trading_strategy.demo_mode,
        "risk_level": trading_strategy.risk_per_trade,
        "open_positions": len(trading_strategy.positions),
        "total_trades": len(trading_strategy.trade_history),
        "consecutive_losses": getattr(trading_strategy, 'consecutive_losses', 0)
    })
    
    # Send trade history to newly connected client
    emit_trade_history()

@socketio.on("disconnect")
def handle_disconnect():
    print(">> Client disconnected")

@socketio.on("toggle_demo_mode")
def handle_toggle_demo_mode():
    demo_mode = trading_strategy.toggle_demo_mode()
    emit("demo_mode_changed", {"demo_mode": demo_mode})

@socketio.on("set_risk_level")
def handle_set_risk_level(data):
    risk_level = data.get("risk", 0.02)
    if trading_strategy.set_risk_level(risk_level):
        emit("risk_level_changed", {"risk_level": risk_level})
    else:
        emit("error", {"message": "Invalid risk level"})

@socketio.on("close_all_positions")
def handle_close_all_positions():
    current_price = current_candle["close"] if current_candle else 0
    closed = trading_strategy.close_all_positions(current_price)
    emit("positions_closed", {"closed_count": len(closed)})
    print(f"Closed {len(closed)} positions")
    
    # Send updated trade history
    emit_trade_history()

@socketio.on("reset_account")
def handle_reset_account():
    """Reset account to initial balance and clear history"""
    new_balance = INITIAL_BALANCE
    trading_strategy.reset_account(new_balance)
    
    # Send reset confirmation
    emit("account_reset", {"new_balance": new_balance})
    
    # Send updated status and history
    current_price = current_candle["close"] if current_candle else 0
    
    emit("trading_status", {
        "enabled": TRADING_ENABLED,
        "strategy": ACTIVE_STRATEGY,
        "balance": trading_strategy.balance,
        "equity": trading_strategy.equity,
        "demo_mode": trading_strategy.demo_mode,
        "risk_level": trading_strategy.risk_per_trade,
        "open_positions": len(trading_strategy.positions),
        "total_trades": len(trading_strategy.trade_history),
        "consecutive_losses": getattr(trading_strategy, 'consecutive_losses', 0)
    })
    
    # Send empty trade history
    emit_trade_history()
    
    print(f"Account reset to ${new_balance}")

# Debug endpoint for testing signals
@socketio.on("debug_signal")
def handle_debug_signal():
    """Debug: Force emit a test signal"""
    test_signal = {
        "signal": "buy", 
        "reason": "DEBUG TEST SIGNAL - Manual trigger",
        "confidence": 85.5,
        "rsi": 65.2,
        "current_price": 1178.39,
        "timestamp": int(time.time())
    }
    
    print("🚀 EMITTING DEBUG SIGNAL TO FRONTEND")
    socketio.emit("trading_signal", test_signal)
    return {"status": "debug_signal_sent", "signal": test_signal}

if __name__ == "__main__":
    ws_thread = threading.Thread(target=start_ws, daemon=True)
    ws_thread.start()
    print(f"Starting server on http://{HOST}:{PORT}")
    print(f"Trading enabled: {TRADING_ENABLED}")
    print(f"Min confidence: {MIN_CONFIDENCE}%")
    socketio.run(app, host=HOST, port=PORT, debug=DEBUG)