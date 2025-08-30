# server.py
import json
import threading
import time
from collections import deque
from typing import Deque, Dict, Any, Optional, List

import websocket
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO

from trade_logic import evaluate_trades

# ───────────────────────────────
# Config — REPLACE API_TOKEN
# ───────────────────────────────
APP_ID = "96293"                     # your app id (optional when using public endpoints)
API_TOKEN = "SdJV9cekZ974RKh"
SYMBOL = "R_100"
CANDLE_INTERVAL = 60                 # 1-minute candles
LOOKBACK = 500                       # how many historical candles to keep

# Auto-trade (paper) settings
AUTOTRADE_ENABLED = True          # toggle paper auto-trading
MIN_CONFIDENCE = 62.0             # minimum confidence to auto-trade
MAX_CONCURRENT_TRADES = 1         # keep it tight for scalping
COOLDOWN_SECS = 45                # cooldown between auto entries

# ───────────────────────────────
# Flask + Socket.IO setup
# ───────────────────────────────
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ───────────────────────────────
# In-memory candle store
# ───────────────────────────────
candles: Deque[Dict[str, Any]] = deque(maxlen=LOOKBACK)  # closed candles
current_candle: Optional[Dict[str, Any]] = None          # forming candle
current_candle_time: Optional[int] = None
last_price: Optional[float] = None

# Paper trading state
open_trades: List[Dict[str, Any]] = []
balance: float = 10000.0

_last_auto_order_ts: Optional[float] = None  # cooldown
_last_signal_payload: Optional[Dict[str, Any]] = None    # for debug/inspect

# ───────────────────────────────
# Helper functions
# ───────────────────────────────
def start_of_minute(epoch: int) -> int:
    return epoch - (epoch % CANDLE_INTERVAL)

def account_snapshot() -> Dict[str, Any]:
    open_pnl = 0.0
    if last_price is not None:
        for t in open_trades:
            if not t.get("open"):
                continue
            # simple PnL calc
            if t["type"] == "BUY":
                open_pnl += (last_price - t["entry"]) * t["lot"]
            else:
                open_pnl += (t["entry"] - last_price) * t["lot"]
    return {
        "balance": float(balance),
        "open_pnl": float(open_pnl),
        "equity": float(balance + open_pnl),
        "last_price": float(last_price) if last_price is not None else None,
        "open_trades": open_trades,
        "autotrade": AUTOTRADE_ENABLED,
        "min_confidence": MIN_CONFIDENCE,
    }

def _close_trade(t: Dict[str, Any], price: float, reason: str):
    global balance
    if not t.get("open"):
        return
    t["open"] = False
    t["exit_price"] = price
    pnl = (price - t["entry"]) * t["lot"] if t["type"] == "BUY" else (t["entry"] - price) * t["lot"]
    balance += pnl
    socketio.emit("trade_closed", {"trade": t, "pnl": float(pnl), "balance": float(balance), "reason": reason})
    socketio.emit("account", account_snapshot())

def _check_tp_sl_exits(price: float):
    # close if price hits TP/SL
    for t in list(open_trades):
        if not t.get("open"):
            continue
        if t.get("take_profit") is not None:
            if t["type"] == "BUY" and price >= t["take_profit"]:
                _close_trade(t, price, "tp")
            elif t["type"] == "SELL" and price <= t["take_profit"]:
                _close_trade(t, price, "tp")
        if t.get("stop_loss") is not None and t.get("open"):
            if t["type"] == "BUY" and price <= t["stop_loss"]:
                _close_trade(t, price, "sl")
            elif t["type"] == "SELL" and price >= t["stop_loss"]:
                _close_trade(t, price, "sl")

def _maybe_auto_trade(signal_payload: Dict[str, Any]):
    global _last_auto_order_ts
    if not AUTOTRADE_ENABLED:
        return
    if signal_payload.get("signal") not in ("BUY", "SELL"):
        return
    conf = signal_payload.get("confidence") or 0.0
    if conf < MIN_CONFIDENCE:
        return
    # limit concurrent trades
    live = [t for t in open_trades if t.get("open")]
    if len(live) >= MAX_CONCURRENT_TRADES:
        return
    # cooldown
    now = time.time()
    if _last_auto_order_ts and (now - _last_auto_order_ts) < COOLDOWN_SECS:
        return

    entry = float(signal_payload.get("entry"))
    lot = float(signal_payload.get("lot") or 1.0)
    sl = signal_payload.get("sl")
    tp = signal_payload.get("tp")
    side = "BUY" if signal_payload["signal"] == "BUY" else "SELL"

    trade = {
        "id": int(time.time() * 1000),
        "symbol": SYMBOL,
        "type": side,
        "entry": entry,
        "lot": lot,
        "take_profit": float(tp) if tp is not None else None,
        "stop_loss": float(sl) if sl is not None else None,
        "open": True,
        "auto": True,
        "meta": {
            "confidence": signal_payload.get("confidence"),
            "reason": signal_payload.get("reason"),
            "atr": signal_payload.get("atr"),
        },
    }
    open_trades.append(trade)
    _last_auto_order_ts = now
    socketio.emit("trade_update", {"open_trades": open_trades, "balance": balance, "auto_entry": True})
    socketio.emit("account", account_snapshot())

def push_or_update_candle_from_tick(epoch: int, price: float):
    """Aggregate 1-minute candles from ticks; emit finalize and live updates."""
    global current_candle, current_candle_time, last_price, _last_signal_payload
    bucket = start_of_minute(epoch)

    # finalize previous candle on minute rollover
    if current_candle_time != bucket:
        if current_candle is not None:
            candles.append(dict(current_candle))           # push closed candle
            socketio.emit("candle", dict(current_candle))  # broadcast closed
        current_candle_time = bucket
        current_candle = {"time": bucket, "open": price, "high": price, "low": price, "close": price}
    else:
        if price > current_candle["high"]:
            current_candle["high"] = price
        if price < current_candle["low"]:
            current_candle["low"] = price
        current_candle["close"] = price

    last_price = price

    # risk/exits before broadcasting snapshot
    _check_tp_sl_exits(price)

    # broadcast live forming candle and account
    socketio.emit("candle", dict(current_candle))
    socketio.emit("account", account_snapshot())

    # ─── Evaluate scalper & emit confidence ───
    signal_payload = evaluate_trades(
        last_price=last_price,
        open_trades=open_trades,
        balance=balance,
        candles=list(candles) + ([current_candle] if current_candle else []),
        params={
            # tweakables if you want different ATR/SL/TP etc.
            "tp_atr_mult": 0.7,
            "sl_atr_mult": 0.5,
            "risk_per_trade": 0.01,
            "min_tick_value": 1.0,
        },
    )
    _last_signal_payload = signal_payload
    socketio.emit("trade_confidence", {
        "confidence": signal_payload.get("confidence"),
        "signal": signal_payload.get("signal"),
        "reason": signal_payload.get("reason"),
    })

    # ─── Paper auto-trade if conditions satisfied ───
    _maybe_auto_trade(signal_payload)

# ───────────────────────────────
# REST endpoints
# ───────────────────────────────
@app.get("/api/health")
def health():
    return jsonify({"ok": True})

@app.get("/api/history")
def api_history():
    data = list(candles)
    if current_candle is not None:
        data = data + [current_candle]
    return jsonify(data)

@app.get("/api/account")
def api_account():
    return jsonify(account_snapshot())

@app.post("/api/autotrade")
def api_autotrade_toggle():
    global AUTOTRADE_ENABLED
    payload = request.get_json(silent=True) or {}
    val = payload.get("enabled")
    if isinstance(val, bool):
        AUTOTRADE_ENABLED = val
    return jsonify({"autotrade": AUTOTRADE_ENABLED})

@app.get("/api/last_signal")
def api_last_signal():
    return jsonify(_last_signal_payload or {})

# ───────────────────────────────
# Socket.IO handlers
# ───────────────────────────────
@socketio.on("connect")
def on_connect():
    print("✅ Client connected")
    hist = sorted(list(candles), key=lambda c: int(c["time"]))
    socketio.emit("history", hist)
    if current_candle is not None:
        socketio.emit("candle", current_candle)
    socketio.emit("account", account_snapshot())

@socketio.on("new_trade")
def on_new_trade(data):
    try:
        trade = {
            "id": int(time.time() * 1000),
            "symbol": data.get("symbol", SYMBOL),
            "type": "BUY" if str(data.get("type")).upper() == "BUY" else "SELL",
            "entry": float(data["entry"]),
            "lot": float(data.get("lot", 1)),
            "take_profit": None if data.get("take_profit") in [None, ""] else float(data.get("take_profit")),
            "stop_loss": None if data.get("stop_loss") in [None, ""] else float(data.get("stop_loss")),
            "open": True,
            "auto": False,
        }
    except Exception as e:
        socketio.emit("trade_update", {"error": f"Invalid trade: {e}"})
        return

    open_trades.append(trade)
    socketio.emit("trade_update", {"open_trades": open_trades, "balance": balance})
    socketio.emit("account", account_snapshot())

@socketio.on("close_trade")
def on_close_trade(data):
    tid = data.get("id")
    price = float(data.get("price", last_price or 0))
    for t in open_trades:
        if t["id"] == tid and t.get("open"):
            _close_trade(t, price, "manual_close")
            return
    socketio.emit("trade_update", {"error": "Trade not found or already closed"})

# ───────────────────────────────
# Deriv WebSocket client (websocket-client)
# ───────────────────────────────
def deriv_on_open(ws):
    print("🔌 Connected to Deriv WS")
    if API_TOKEN:
        ws.send(json.dumps({"authorize": API_TOKEN}))
    else:
        ws.send(json.dumps({
            "ticks_history": SYMBOL,
            "style": "candles",
            "granularity": CANDLE_INTERVAL,
            "count": LOOKBACK,
            "end": "latest",
            "adjust_start_time": 1
        }))
        ws.send(json.dumps({"ticks": SYMBOL, "subscribe": 1}))

def deriv_on_message(ws, message):
    try:
        msg = json.loads(message)
    except Exception as e:
        print("JSON parse error:", e)
        return

    mt = msg.get("msg_type")
    if mt == "authorize":
        ws.send(json.dumps({
            "ticks_history": SYMBOL,
            "style": "candles",
            "granularity": CANDLE_INTERVAL,
            "count": LOOKBACK,
            "end": "latest",
            "adjust_start_time": 1
        }))
        ws.send(json.dumps({"ticks": SYMBOL, "subscribe": 1}))
        return

    if mt == "candles":
        rows = [{
            "time": int(c["epoch"]),
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low":  float(c["low"]),
            "close": float(c["close"]),
        } for c in msg.get("candles", [])]
        candles.clear()
        for r in rows[-LOOKBACK:]:
            candles.append(r)
        global current_candle_time, current_candle, last_price
        current_candle_time = None
        current_candle = None
        if candles:
            last_price = candles[-1]["close"]
            socketio.emit("account", account_snapshot())
        socketio.emit("history", sorted(list(candles), key=lambda c: int(c["time"])))
        print(f"📊 Sent {len(candles)} historical candles")

    if mt == "tick":
        t = msg["tick"]
        epoch = int(t["epoch"])
        price = float(t["quote"])
        push_or_update_candle_from_tick(epoch, price)

    if mt == "error":
        print("❌ Deriv error:", msg.get("error"))

def deriv_on_close(ws, code, reason):
    print("🔌 Deriv WS closed:", code, reason)
    time.sleep(3)
    run_deriv_ws()

def deriv_on_error(ws, error):
    print("⚠️ Deriv WS error:", error)

def run_deriv_ws():
    url = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"
    ws = websocket.WebSocketApp(
        url,
        on_open=deriv_on_open,
        on_message=deriv_on_message,
        on_close=deriv_on_close,
        on_error=deriv_on_error,
    )
    ws.run_forever()

def start_deriv_thread():
    t = threading.Thread(target=run_deriv_ws, daemon=True)
    t.start()

# ───────────────────────────────
# Main
# ───────────────────────────────
if __name__ == "__main__":
    start_deriv_thread()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
