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
SYMBOL = "R_100"                 # Volatility index
TIMEFRAME = 300                  # seconds per candle (5m)
LOOKBACK = 300                   # number of candles to check for FVG/swing
PING_SECONDS = 30
RECONNECT_WAIT = 5
CSV_FILE = "historical_data.csv"
TRADES_FILE = "trade_signals.csv"

# ======= RISK / TRADE MGMT =======
ATR_PERIOD = 14
ATR_MULT_SL = 1.2
RR_TARGET = 2.0
MIN_SL_POINTS = 2.0
PARTIAL_AT_R = 1.0
PARTIAL_PCT = 0.5
TRAIL_AFTER_BE = True
TRAIL_ATR_MULT = 1.0
PRINT_TABLE_EVERY_TICKS = 10
MAX_SAFE_STAKE = 1.0  # Demo account safe stake

# ======= GLOBAL STATE =======
if os.path.exists(CSV_FILE):
    historical_data = pd.read_csv(CSV_FILE, parse_dates=["datetime"])
else:
    historical_data = pd.DataFrame(columns=["datetime", "open", "high", "low", "close"])

current_candle = None
lock = threading.Lock()
stop_flag = threading.Event()
ping_timer = None
traded_fvgs = set()
_tick_counter = 0

# Win rate tracking
closed_trades_count = 0
wins_count = 0

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

# ======= INDICATORS =======
def compute_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> float:
    if len(df) < period + 1:
        recent = df.tail(max(5, period))
        return max((recent["high"] - recent["low"]).mean(), MIN_SL_POINTS)
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    trs = []
    for i in range(1, len(df)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)
    atr_series = pd.Series(trs).rolling(period).mean()
    last_atr = atr_series.iloc[-1]
    if pd.isna(last_atr) or last_atr <= 0:
        recent = df.tail(max(5, period))
        last_atr = (recent["high"] - recent["low"]).mean()
    return max(float(last_atr), MIN_SL_POINTS)

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
def build_trade_row(side: str, price: float, atr: float, fvg_id: str):
    sl_dist = max(atr * ATR_MULT_SL, MIN_SL_POINTS)
    if side == "BUY":
        sl = price - sl_dist
        tp = price + sl_dist * RR_TARGET
    else:
        sl = price + sl_dist
        tp = price - sl_dist * RR_TARGET
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": side,
        "price": price,
        "sl": sl,
        "tp": tp,
        "status": "OPEN",
        "pnl": 0.0,
        "fvg_id": fvg_id,
        "atr": atr,
        "risk": sl_dist,
        "rr": RR_TARGET,
        "be_moved": 0,
        "partial_taken": 0,
        "trail_active": 0,
        "trail_level": sl,
        "qty": MAX_SAFE_STAKE,
        "qty_open": MAX_SAFE_STAKE,
        "realized_pnl": 0.0,
        "max_favorable_excursion": 0.0
    }

def check_trade_signals(candles, swing_highs, swing_lows, fvgs):
    global traded_fvgs
    signals = []
    if len(candles) == 0 or not fvgs:
        return signals
    last_candle = candles.iloc[-1]
    current_price = last_candle["close"]
    last_fvg = fvgs[-1]
    fvg_id = f"{last_fvg['start_time']}{last_fvg['type']}"
    if fvg_id in traded_fvgs:
        return signals
    atr = compute_atr(candles.tail(max(ATR_PERIOD + 2, 50)))
    if last_fvg["type"] == "Bullish" and current_price >= last_fvg["start_price"]:
        trade = build_trade_row("BUY", float(current_price), atr, fvg_id)
        signals.append(trade)
        traded_fvgs.add(fvg_id)
    elif last_fvg["type"] == "Bearish" and current_price <= last_fvg["end_price"]:
        trade = build_trade_row("SELL", float(current_price), atr, fvg_id)
        signals.append(trade)
        traded_fvgs.add(fvg_id)
    return signals

def save_trade_signals(signals):
    if not signals:
        return
    columns = ["timestamp","action","price","sl","tp","status","pnl","fvg_id",
               "atr","risk","rr","be_moved","partial_taken","trail_active",
               "trail_level","qty","qty_open","realized_pnl","max_favorable_excursion"]
    df = pd.DataFrame(signals)
    for col in columns:
        if col not in df.columns:
            df[col] = 0
    df = df[columns]
    file_exists = os.path.exists(TRADES_FILE)
    df.to_csv(TRADES_FILE, mode="a", header=not file_exists, index=False)

# ======= DERIV TRADE PLACEMENT =======
def place_deriv_trade(ws, trade):
    side = trade["action"]
    contract_type = "CALL" if side == "BUY" else "PUT"
    safe_qty = min(trade["qty"], MAX_SAFE_STAKE)
    buy_request = {
        "buy": 1,
        "subscribe": 1,
        "price": 0,
        "parameters": {
            "amount": safe_qty,
            "contract_type": contract_type,
            "symbol": SYMBOL,
            "duration": TIMEFRAME // 60,
            "duration_unit": "m",
            "basis": "stake",
            "currency": "USD"
        }
    }
    print("🚀 Placing Trades:", [{"action": side, "price": trade["price"], "qty": safe_qty}])
    ws_send(ws, buy_request)

# ======= TICK & CANDLE LOGIC =======
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
            return
        if current_candle["datetime"] == candle_start_dt:
            current_candle["high"] = max(current_candle["high"], price)
            current_candle["low"]  = min(current_candle["low"],  price)
            current_candle["close"] = price
        else:
            finished = current_candle
            current_candle = {"datetime": candle_start_dt, "open": price, "high": price, "low": price, "close": price}

    if finished:
        on_new_closed_candle(finished)

def on_new_closed_candle(candle: dict):
    global historical_data
    with lock:
        row = pd.DataFrame([candle], columns=historical_data.columns)
        historical_data = pd.concat([historical_data, row], ignore_index=True)
        file_exists = os.path.exists(CSV_FILE)
        pd.DataFrame([candle]).to_csv(CSV_FILE, mode="a", header=not file_exists, index=False)
        print("📝 New candle added:", candle)

        start_idx = max(len(historical_data) - LOOKBACK, 0)
        recent = historical_data.iloc[start_idx:].reset_index(drop=True)

    swing_highs, swing_lows = detect_swing_points(recent)
    fvgs = detect_fvg(recent)
    signals = check_trade_signals(recent, swing_highs, swing_lows, fvgs)
    if signals:
        print("🚀 Trade Signals:", [{"action": s["action"], "price": s["price"], "sl": s["sl"], "tp": s["tp"]} for s in signals])
        save_trade_signals(signals)
        for trade in signals:
            place_deriv_trade(current_ws, trade)  # Use the live WS to place trade

# ======= WS CALLBACKS =======
def on_open(ws):
    global current_ws
    current_ws = ws
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
    print(f"🔌 Connection closed ({close_status_code}):", close_msg)
    cancel_ping()
    time.sleep(RECONNECT_WAIT)
    start_ws()

def start_ws():
    ws = websocket.WebSocketApp(
        "wss://ws.binaryws.com/websockets/v3?app_id=" + APP_ID,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()

# ======= GRACEFUL SHUTDOWN =======
def signal_handler(sig, frame):
    print("\n🛑 Shutting down...")
    stop_flag.set()
    cancel_ping()
    time.sleep(1)
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ======= START =======
if __name__ == "__main__":
    print("💹 Starting Dynamic Trading Bot…")
    start_ws()
