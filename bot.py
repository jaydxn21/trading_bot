# bot.py - Core Engine
import json
import websocket
import threading
import numpy as np
from flask import Flask
from flask_socketio import SocketIO
from config import *
from strategies import STRATEGIES
from utils.indicators import calculate_common_indicators
from utils.helpers import create_new_candle, update_current_candle
from historicalData import fetch_historical_candles

# ───────── Flask Setup ─────────
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

candles, current_candle = [], None
is_authorized = False
historical_data_loaded = False  # Track if historical data is loaded

# ───────── Format Candles for Lightweight-Charts ─────────
def format_candles(candles_list):
    """Format candles for lightweight-charts."""
    formatted = []
    for c in candles_list:
        ts = int(c.get("timestamp", c.get("epoch", 0)))
        # Normalize time → must be seconds
        if ts > 1e12:   # ms to s
            ts = ts // 1000
        elif ts > 2000000000:  # fallback check
            ts = ts // 1000
        formatted.append({
            "time": ts,
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
            "volume": int(c.get("volume", 0)),
        })
    return formatted

# ───────── Load Historical Data ─────────
def load_historical_data():
    global candles, current_candle, historical_data_loaded
    print("[Historical] Fetching historical candles...")
    hist_candles = fetch_historical_candles(symbol=SYMBOL, granularity=GRANULARITY, count=HISTORY_COUNT)

    if hist_candles:
        # Ensure timestamp exists
        for c in hist_candles:
            if "epoch" in c and "timestamp" not in c:
                c["timestamp"] = c["epoch"]

        candles = hist_candles
        current_candle = candles[-1].copy() if candles else None
        historical_data_loaded = True
        print(f"[Historical] Loaded {len(candles)} candles")
        print("[SOCKET] First 3 candles:", format_candles(candles)[:3])  # DEBUG
    else:
        print("[Historical] No historical data received")

# ───────── WebSocket Callbacks ─────────
def on_open(ws):
    print("[DerivWS] Connected")
    ws.send(json.dumps({"authorize": API_TOKEN}))

def on_message(ws, message):
    global candles, current_candle, is_authorized
    try:
        data = json.loads(message)
        msg_type = data.get("msg_type")
        print(f"[DerivWS] Received message type: {msg_type}")

        if msg_type == "authorize":
            is_authorized = True
            print("[DerivWS] Authorized")
            # Start live tick stream
            ws.send(json.dumps({"ticks": SYMBOL, "subscribe": 1}))

        elif msg_type == "tick":
            tick = data.get("tick")
            if tick:
                process_tick(tick)

        else:
            print(f"[DerivWS] Unhandled message type: {msg_type} | data: {data}")

    except Exception as e:
        print(f"[ERROR] Exception in on_message: {e}")

# ───────── Tick Processing ─────────
def process_tick(tick):
    global candles, current_candle
    try:
        candle_time = tick["epoch"] - (tick["epoch"] % GRANULARITY)

        if current_candle is None:
            current_candle = create_new_candle(tick, timeframe=GRANULARITY)
            candles.append(current_candle)

        elif candle_time > current_candle["timestamp"]:
            # Calculate indicators
            if len(candles) >= 20:  # Minimum candles for most indicators
                closes = np.array([c["close"] for c in candles])
                highs = np.array([c["high"] for c in candles])
                lows = np.array([c["low"] for c in candles])

                indicators = calculate_common_indicators(highs, lows, closes)

                # Run all strategies
                for name, strategy in STRATEGIES.items():
                    signal = strategy.analyze_market(candles, tick["quote"], indicators)
                    socketio.emit("trading_signal", {"strategy": name, **signal})
                    trade = strategy.execute_trade(signal, tick["quote"])
                    if trade:
                        socketio.emit("trade_executed", trade)

            # Start new candle
            current_candle = create_new_candle(tick, timeframe=GRANULARITY)
            candles.append(current_candle)
            if len(candles) > HISTORY_COUNT:
                candles.pop(0)

        else:
            update_current_candle(current_candle, tick)

        # Emit latest candle to clients
        formatted = format_candles([current_candle])[-1]
        socketio.emit("candle_update", formatted)

    except Exception as e:
        print(f"[ERROR] Exception in process_tick: {e}")

# ───────── Run WebSocket ─────────
def start_ws():
    ws = websocket.WebSocketApp(DERIV_WS_URL, on_open=on_open, on_message=on_message)
    ws.run_forever()

# ───────── SocketIO Connect ─────────
@socketio.on("connect")
def handle_connect():
    print("[SOCKET] Client connected")
    if historical_data_loaded and candles:
        formatted = format_candles(candles)
        socketio.emit("candles", formatted)
        print(f"[SOCKET] Emitting {len(formatted)} historical candles to new client")

# ───────── Flask Route ─────────
@app.route("/")
def index():
    return "Trading Bot Running!"

# ───────── Main ─────────
if __name__ == "__main__":
    load_historical_data()  # fetch historical candles first
    threading.Thread(target=start_ws, daemon=True).start()
    socketio.run(app, host=HOST, port=PORT)