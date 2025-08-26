import json
import threading
import time
from collections import deque

import websocket
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# ───────────────────────────────
# Config
# ───────────────────────────────
APP_ID = "96293"
API_TOKEN = "ny0HL5uKOZrOx9F"
SYMBOL = "R_100"
CANDLE_INTERVAL = 60     # 1-minute candles
LOOKBACK = 200           # historical candles to keep/emit

# ───────────────────────────────
# Flask + Socket.IO
# ───────────────────────────────
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

# ───────────────────────────────
# Market / Candle storage
# ───────────────────────────────
candles = deque(maxlen=LOOKBACK)  # closed candles
current_candle = None             # active candle this minute
current_candle_time = None        # epoch (start of minute) for current candle
last_price = None                 # last traded price (from ticks / candle close)

# ───────────────────────────────
# Trading state (demo)
# ───────────────────────────────
open_trades = []  # list of dicts: id, symbol, type, entry, lot, take_profit, stop_loss, open
balance = 10000.0

# ───────────────────────────────
# Utility
# ───────────────────────────────
def start_of_minute(epoch: int) -> int:
    return epoch - (epoch % CANDLE_INTERVAL)

def compute_open_pnl(price: float) -> float:
    """Sum unrealized PnL for all open trades at given price."""
    if price is None:
        return 0.0
    pnl = 0.0
    for t in open_trades:
        if t.get("open"):
            if t["type"] == "BUY":
                pnl += (price - t["entry"]) * t["lot"]
            else:
                pnl += (t["entry"] - price) * t["lot"]
    return pnl

def snapshot_and_broadcast():
    """Emit a single 'account' snapshot to all clients."""
    open_pnl = compute_open_pnl(last_price)
    equity = balance + open_pnl
    payload = {
        "balance": float(balance),
        "open_pnl": float(open_pnl),
        "equity": float(equity),
        "last_price": float(last_price) if last_price is not None else None,
        "open_trades": open_trades,
    }
    socketio.emit("account", payload)

def close_trade_internal(trade, exit_price: float, reason: str = "manual"):
    """Finalize a trade, update balance, notify clients."""
    global balance
    if not trade.get("open"):
        return
    trade["open"] = False
    trade["exit_price"] = float(exit_price)
    pnl = (exit_price - trade["entry"]) * trade["lot"] if trade["type"] == "BUY" else (trade["entry"] - exit_price) * trade["lot"]
    balance += pnl
    socketio.emit("trade_closed", {"trade": trade, "pnl": float(pnl), "balance": float(balance), "reason": reason}, broadcast=True)
    snapshot_and_broadcast()

def auto_close_if_hit(price: float):
    """Check TP/SL for all open trades and close if hit."""
    # copy list to avoid mutation during iteration
    for t in list(open_trades):
        if not t.get("open"):
            continue
        tp = t.get("take_profit")
        sl = t.get("stop_loss")
        if t["type"] == "BUY":
            if tp is not None and price >= tp:
                close_trade_internal(t, price, reason="TP")
            elif sl is not None and price <= sl:
                close_trade_internal(t, price, reason="SL")
        else:  # SELL
            if tp is not None and price <= tp:
                close_trade_internal(t, price, reason="TP")
            elif sl is not None and price >= sl:
                close_trade_internal(t, price, reason="SL")

def push_or_update_candle_from_tick(epoch: int, price: float):
    """Update the in-progress M1 candle with this tick; if minute rolls, finalize previous."""
    global current_candle, current_candle_time, last_price

    bucket = start_of_minute(epoch)

    if current_candle_time != bucket:
        # finalize previous candle
        if current_candle is not None:
            candles.append(current_candle)
            socketio.emit("candle", current_candle)
        # start new candle
        current_candle_time = bucket
        current_candle = {
            "time": bucket,
            "open": price,
            "high": price,
            "low":  price,
            "close": price,
        }
    else:
        # update current candle
        if price > current_candle["high"]:
            current_candle["high"] = price
        if price < current_candle["low"]:
            current_candle["low"] = price
        current_candle["close"] = price

    last_price = price
    # Emit live candle update
    socketio.emit("candle", current_candle)
    # Auto-close checks and account snapshot
    auto_close_if_hit(price)
    snapshot_and_broadcast()

# ───────────────────────────────
# Socket.IO: client lifecycle & trade events
# ───────────────────────────────
@socketio.on("connect")
def on_connect():
    print("✅ Client connected")
    # Send historical closed candles
    if candles:
        emit("candle", list(candles))
    # Send current forming candle
    if current_candle:
        emit("candle", current_candle)
    # Send account snapshot
    snapshot_and_broadcast()

@socketio.on("new_trade")
def handle_new_trade(data):
    """
    data: {symbol, type: 'BUY'|'SELL', entry, lot, take_profit?, stop_loss?}
    """
    global open_trades
    try:
        trade = {
            "id": int(time.time() * 1000),
            "symbol": data.get("symbol", SYMBOL),
            "type": "BUY" if str(data.get("type")).upper() == "BUY" else "SELL",
            "entry": float(data["entry"]),
            "lot": float(data.get("lot", 1)),
            "take_profit": None if data.get("take_profit") in [None, ""] else float(data.get("take_profit")),
            "stop_loss":  None if data.get("stop_loss")  in [None, ""] else float(data.get("stop_loss")),
            "open": True,
        }
    except Exception as e:
        emit("trade_update", {"error": f"Invalid trade: {e}"})
        return

    open_trades.append(trade)
    socketio.emit("trade_update", {"open_trades": open_trades, "balance": balance}, broadcast=True)
    snapshot_and_broadcast()

@socketio.on("close_trade")
def handle_close_trade(data):
    """
    data: {id, price}
    """
    tid = data.get("id")
    price = float(data.get("price"))
    for t in open_trades:
        if t["id"] == tid and t.get("open"):
            close_trade_internal(t, price, reason="manual")
            return
    emit("trade_update", {"error": "Trade not found or already closed"})

# ───────────────────────────────
# Deriv WebSocket handlers
# ───────────────────────────────
def deriv_on_message(ws, message):
    global candles, current_candle, current_candle_time, last_price
    try:
        msg = json.loads(message)
    except Exception as e:
        print("JSON parse error:", e)
        return

    mt = msg.get("msg_type")

    if mt == "authorize":
        print("🔑 Authorized with Deriv")

        # Request historical M1 candles (closed)
        ws.send(json.dumps({
            "ticks_history": SYMBOL,
            "style": "candles",
            "granularity": CANDLE_INTERVAL,
            "count": LOOKBACK,
            "end": "latest",
            "adjust_start_time": 1
        }))

        # Subscribe to live ticks
        ws.send(json.dumps({"ticks": SYMBOL, "subscribe": 1}))

    elif mt == "candles":
        rows = [{
            "time": int(c["epoch"]),
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low":  float(c["low"]),
            "close": float(c["close"]),
        } for c in msg["candles"]]

        candles.clear()
        for r in rows[-LOOKBACK:]:
            candles.append(r)

        socketio.emit("candle", list(candles))
        print(f"📊 Loaded & sent {len(candles)} historical candles")

        current_candle = None
        current_candle_time = None
        # Last price from last closed candle
        if candles:
            last_price = candles[-1]["close"]
            snapshot_and_broadcast()

    elif mt == "tick":
        tick = msg["tick"]
        epoch = int(tick["epoch"])   # seconds
        price = float(tick["quote"])
        push_or_update_candle_from_tick(epoch, price)

    elif mt == "error":
        print("❌ Deriv error:", msg["error"]["message"])

def deriv_on_open(ws):
    print("🔌 Connected to Deriv WS")
    ws.send(json.dumps({"authorize": API_TOKEN}))

def deriv_on_close(ws, code, reason):
    print("🔌 Deriv WS closed:", code, reason)

def deriv_on_error(ws, error):
    print("⚠️ Deriv WS error:", error)

def start_deriv_ws():
    url = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"
    ws = websocket.WebSocketApp(
        url,
        on_open=deriv_on_open,
        on_message=deriv_on_message,
        on_close=deriv_on_close,
        on_error=deriv_on_error,
    )
    ws.run_forever()

def boot():
    t = threading.Thread(target=start_deriv_ws, daemon=True)
    t.start()

# ───────────────────────────────
# Run
# ───────────────────────────────
if __name__ == "__main__":
    boot()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True,
                 use_reloader=False, allow_unsafe_werkzeug=True)
