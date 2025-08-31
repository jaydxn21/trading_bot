import json
import websocket
import threading
import time
from flask import Flask
from flask_socketio import SocketIO, emit

# ───────── Config ─────────
APP_ID = "96293"              # Replace with your Deriv App ID
API_TOKEN = "vTHHpERJcDMDu0f"   # Replace with your Deriv API Token
SYMBOL = "R_100"               # Example: Synthetic Index
GRANULARITY = 60               # 1-minute candles (60 seconds)
HISTORY_COUNT = 100

# ───────── Flask + SocketIO ─────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

candles = []  # Store historical + live candles
current_candle = None
ws_connection = None
is_authorized = False

# ───────── WebSocket callbacks ─────────
def on_open(ws):
    global ws_connection
    ws_connection = ws
    print("[DerivWS] Connected")
    # First step: authorize
    ws.send(json.dumps({"authorize": API_TOKEN}))

def on_message(ws, message):
    global candles, current_candle, is_authorized
    data = json.loads(message)
    print(f"Received message type: {data.get('msg_type')}")
    
    # Handle authorization response
    if data.get("msg_type") == "authorize":
        is_authorized = True
        print("[DerivWS] Authorized successfully")
        
        # Request historical candles first
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
        
        # Set the current candle to the last historical candle
        if candles:
            current_candle = candles[-1].copy()
            print(f"Current candle set to: {current_candle['epoch']}")
        
        # Format and send to frontend
        formatted_candles = format_candles(candles)
        socketio.emit("candles", formatted_candles)
        
        # Now subscribe to live ticks
        print("Subscribing to live ticks...")
        ws.send(json.dumps({
            "ticks": SYMBOL,
            "subscribe": 1
        }))
    
    # Live ticks for candle updates
    elif data.get("msg_type") == "tick":
        tick = data["tick"]
        print(f"Received tick: {tick['epoch']} - {tick['quote']}")
        process_tick(tick)
    
    # Error handling
    elif data.get("error"):
        print(f"Error received: {data['error']}")

def process_tick(tick):
    global candles, current_candle
    
    epoch = tick["epoch"]
    price = float(tick["quote"])
    
    # Calculate the candle time for this tick (start of the minute)
    candle_time = epoch - (epoch % GRANULARITY)
    
    # If we don't have a current candle, create one
    if current_candle is None:
        current_candle = {
            "epoch": candle_time,
            "open": price,
            "high": price,
            "low": price,
            "close": price
        }
        candles.append(current_candle)
        print(f"Created new candle at {candle_time}")
    
    # Check if we need to create a new candle (new minute)
    elif candle_time > current_candle["epoch"]:
        # Finalize the current candle
        print(f"Closing candle at {current_candle['epoch']}, open: {current_candle['open']}, close: {current_candle['close']}")
        
        # Create a new candle
        current_candle = {
            "epoch": candle_time,
            "open": price,
            "high": price,
            "low": price,
            "close": price
        }
        candles.append(current_candle)
        print(f"Created new candle at {candle_time}")
        
        # Keep only the most recent candles
        if len(candles) > HISTORY_COUNT:
            candles.pop(0)
    else:
        # Update the current candle with the new tick
        current_candle["close"] = price
        if price > current_candle["high"]:
            current_candle["high"] = price
        if price < current_candle["low"]:
            current_candle["low"] = price
    
    # Send updated candles to frontend - but only send the latest candle for real-time updates
    # This prevents resetting the chart position
    socketio.emit("candle_update", {
        "time": current_candle["epoch"],
        "open": float(current_candle["open"]),
        "high": float(current_candle["high"]),
        "low": float(current_candle["low"]),
        "close": float(current_candle["close"])
    })

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
        formatted_candles = format_candles(candles)
        emit("candles", formatted_candles)

@socketio.on("disconnect")
def handle_disconnect():
    print(">> Client disconnected")

# ───────── Main ─────────
if __name__ == "__main__":
    ws_thread = threading.Thread(target=start_ws, daemon=True)
    ws_thread.start()
    
    # Start Flask-SocketIO server
    print("Starting server on http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)