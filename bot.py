import json
import time
import signal
import threading
from datetime import datetime, timezone
import pandas as pd
import websocket
import os
from tabulate import tabulate  # pip install tabulate

# ======= CONFIG =======
APP_ID = "96293"
API_TOKEN = "QugfW3vy02W7SXa"
SYMBOL = "R_100"          # e.g., Volatility indices
TIMEFRAME = 300           # seconds per candle (e.g., 300 = 5m)
LOOKBACK = 10             # recent candles to check for swing/FVG
PING_SECONDS = 30         # JSON ping cadence to keep socket alive
RECONNECT_WAIT = 5        # seconds to wait before reconnect
CSV_FILE = "historical_data.csv"
TRADES_FILE = "trade_signals.csv"

# ======= GLOBAL STATE =======
if os.path.exists(CSV_FILE):
    historical_data = pd.read_csv(CSV_FILE, parse_dates=["datetime"])
else:
    historical_data = pd.DataFrame(columns=["datetime", "open", "high", "low", "close"])

current_candle = None
lock = threading.Lock()
stop_flag = threading.Event()
ping_timer = None

# Track FVGs that already triggered trades
traded_fvgs = set()

# ======= UTIL =======
def ws_send(ws, data: dict):
    try:
        ws.send(json.dumps(data))
    except Exception as e:
        print("❌ Send failed:", e)

def epoch_to_floor(ts_epoch: int, frame: int) -> int:
    return (ts_epoch // frame) * frame

def schedule_ping(ws):
    global ping_timer
    if stop_flag.is_set():
        return
    ws_send(ws, {"ping": 1})
    ping_timer = threading.Timer(PING_SECONDS, lambda: schedule_ping(ws))
    ping_timer.daemon = True
    ping_timer.start()

def cancel_ping():
    global ping_timer
    if ping_timer:
        ping_timer.cancel()
        ping_timer = None

# ======= ANALYTICS =======
def detect_swing_points(df: pd.DataFrame, left=2, right=2):
    swing_highs, swing_lows = [], []
    if len(df) < left + right + 1:
        return swing_highs, swing_lows

    for i in range(left, len(df) - right):
        high = df["high"].iloc[i]
        low  = df["low"].iloc[i]
        if all(high > df["high"].iloc[i - j - 1] for j in range(left)) and \
           all(high > df["high"].iloc[i + j + 1] for j in range(right)):
            swing_highs.append((df["datetime"].iloc[i], high))
        if all(low < df["low"].iloc[i - j - 1] for j in range(left)) and \
           all(low  < df["low"].iloc[i + j + 1] for j in range(right)):
            swing_lows.append((df["datetime"].iloc[i], low))
    return swing_highs, swing_lows

def detect_fvg(df: pd.DataFrame):
    fvg_list = []
    if len(df) < 3:
        return fvg_list
    for i in range(2, len(df)):
        if df["low"].iloc[i] > df["high"].iloc[i - 2]:
            fvg_list.append({
                "type": "Bullish",
                "start_time": df["datetime"].iloc[i - 2],
                "end_time":   df["datetime"].iloc[i],
                "start_price": float(df["high"].iloc[i - 2]),
                "end_price":   float(df["low"].iloc[i]),
                "gap": float(df["low"].iloc[i] - df["high"].iloc[i - 2]),
            })
        if df["high"].iloc[i] < df["low"].iloc[i - 2]:
            fvg_list.append({
                "type": "Bearish",
                "start_time": df["datetime"].iloc[i - 2],
                "end_time":   df["datetime"].iloc[i],
                "start_price": float(df["high"].iloc[i]),
                "end_price":   float(df["low"].iloc[i - 2]),
                "gap": float(df["low"].iloc[i - 2] - df["high"].iloc[i]),
            })
    return fvg_list

# ======= TRADE LOGIC =======
def check_trade_signals(candles, swing_highs, swing_lows, fvgs):
    global traded_fvgs
    signals = []
    if len(candles) == 0 or not fvgs:
        return signals

    last_candle = candles.iloc[-1]
    current_price = last_candle["close"]

    last_swing_high = swing_highs[-1][1] if swing_highs else None
    last_swing_low = swing_lows[-1][1] if swing_lows else None
    last_fvg = fvgs[-1]

    # Use the FVG start_time + type as a unique ID
    fvg_id = str(last_fvg["start_time"]) + last_fvg["type"]
    if fvg_id in traded_fvgs:
        return signals  # Already traded this FVG

    if last_fvg["type"] == "Bullish" and last_swing_low and current_price >= last_fvg["start_price"]:
        sl = last_swing_low
        tp = current_price + (current_price - sl) * 2
        signals.append({
            "timestamp": datetime.now(),
            "action": "BUY",
            "price": current_price,
            "sl": sl,
            "tp": tp,
            "status": "OPEN",
            "pnl": 0,
            "fvg_id": fvg_id
        })
        traded_fvgs.add(fvg_id)

    elif last_fvg["type"] == "Bearish" and last_swing_high and current_price <= last_fvg["end_price"]:
        sl = last_swing_high
        tp = current_price - (sl - current_price) * 2
        signals.append({
            "timestamp": datetime.now(),
            "action": "SELL",
            "price": current_price,
            "sl": sl,
            "tp": tp,
            "status": "OPEN",
            "pnl": 0,
            "fvg_id": fvg_id
        })
        traded_fvgs.add(fvg_id)

    return signals

def save_trade_signals(signals):
    if not signals:
        return
    columns = ["timestamp", "action", "price", "sl", "tp", "status", "pnl", "fvg_id"]
    df = pd.DataFrame(signals, columns=columns)
    file_exists = os.path.exists(TRADES_FILE)
    df.to_csv(TRADES_FILE, mode="a", header=not file_exists, index=False)

# ======= LIVE PnL & SL/TP WITH TABLE =======
def update_open_trades(current_price):
    if not os.path.exists(TRADES_FILE):
        return

    global traded_fvgs
    df = pd.read_csv(TRADES_FILE)
    table_rows = []

    for idx, row in df.iterrows():
        if row.get("status") == "CLOSED":
            continue

        action = row["action"]
        sl = float(row["sl"])
        tp = float(row["tp"])
        entry_price = float(row["price"])
        fvg_id = row.get("fvg_id", None)

        pnl = 0
        closed = False

        if action == "BUY":
            pnl = current_price - entry_price
            if current_price <= sl or current_price >= tp:
                closed = True
        elif action == "SELL":
            pnl = entry_price - current_price
            if current_price >= sl or current_price <= tp:
                closed = True

        df.at[idx, "pnl"] = pnl

        if closed:
            df.at[idx, "status"] = "CLOSED"
            # Remove FVG from the set so it can be used again
            if fvg_id and fvg_id in traded_fvgs:
                traded_fvgs.remove(fvg_id)

        table_rows.append([
            row["timestamp"], action, entry_price, sl, tp, current_price, pnl, df.at[idx, "status"]
        ])

    df.to_csv(TRADES_FILE, index=False)

    if table_rows:
        print("\n📋 Current Open Trades:")
        print(tabulate(table_rows, headers=["Time", "Action", "Entry", "SL", "TP", "Current", "PnL", "Status"], tablefmt="fancy_grid"))

# ======= CANDLE BUILDER =======
def save_candle_to_csv(candle):
    df = pd.DataFrame([candle])
    file_exists = os.path.exists(CSV_FILE)
    df.to_csv(CSV_FILE, mode="a", header=not file_exists, index=False)

def on_new_closed_candle(candle: dict):
    global historical_data
    with lock:
        row = pd.DataFrame([candle], columns=historical_data.columns)
        historical_data = pd.concat([historical_data, row], ignore_index=True)
        save_candle_to_csv(candle)
        print("📝 New candle added:", candle)

        start_idx = max(len(historical_data) - LOOKBACK - 4, 0)
        recent = historical_data.iloc[start_idx:].reset_index(drop=True)

    swing_highs, swing_lows = detect_swing_points(recent)
    fvgs = detect_fvg(recent)

    signals = check_trade_signals(recent, swing_highs, swing_lows, fvgs)
    if signals:
        print("🚀 Trade Signals:", signals)
        save_trade_signals(signals)

# ======= TICK HANDLING =======
def update_with_tick(tick: dict):
    global current_candle
    ts_epoch = int(tick["epoch"])
    price = float(tick["quote"])
    candle_start_epoch = epoch_to_floor(ts_epoch, TIMEFRAME)
    candle_start_dt = datetime.fromtimestamp(candle_start_epoch, tz=timezone.utc).replace(tzinfo=None)

    finished = None
    with lock:
        if current_candle is None:
            current_candle = {"datetime": candle_start_dt, "open": price, "high": price, "low": price, "close": price}
            update_open_trades(price)
            return

        if current_candle["datetime"] == candle_start_dt:
            current_candle["high"] = max(current_candle["high"], price)
            current_candle["low"]  = min(current_candle["low"],  price)
            current_candle["close"] = price
        else:
            finished = current_candle
            current_candle = {"datetime": candle_start_dt, "open": price, "high": price, "low": price, "close": price}

    update_open_trades(price)

    if finished:
        on_new_closed_candle(finished)

# ======= WS CALLBACKS =======
def on_open(ws):
    print("✅ Connected to Deriv API")
    ws_send(ws, {"authorize": API_TOKEN})

def on_message(ws, message):
    msg = json.loads(message)
    mtype = msg.get("msg_type")

    if mtype == "authorize":
        print("🔑 Authorized. Subscribing to live ticks…")
        schedule_ping(ws)
        ws_send(ws, {"ticks": SYMBOL, "subscribe": 1})

    elif mtype == "tick" and "tick" in msg:
        update_with_tick(msg["tick"])

    elif mtype == "ping":
        pass

    elif "error" in msg:
        print("❌ API error:", msg.get("error"))

def on_error(ws, error):
    print("❌ WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print(f"🔌 Connection closed ({close_status_code}): {close_msg}")
    cancel_ping()

# ======= RUN / RECONNECT LOOP =======
def run_ws():
    while not stop_flag.is_set():
        try:
            ws = websocket.WebSocketApp(
                f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}",
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.run_forever(ping_interval=20, ping_timeout=10)
        except Exception as e:
            print("🔁 Socket crashed, retrying in", RECONNECT_WAIT, "s. Reason:", e)
        if not stop_flag.is_set():
            time.sleep(RECONNECT_WAIT)

def handle_sigint(sig, frame):
    print("\n🧹 Shutting down…")
    stop_flag.set()
    cancel_ping()

# ======= MAIN =======
if __name__ == "__main__":
    try:
        signal.signal(signal.SIGINT, handle_sigint)
    except Exception:
        pass
    run_ws()
