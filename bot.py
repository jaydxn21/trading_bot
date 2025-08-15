import websocket
import json
import numpy as np

# ───────────────────────────
# Config
# ───────────────────────────
DERIV_TOKEN = "FscvuORyE062Izc"  # Replace with your real token
APP_ID = 96293
SYMBOL = "R_100"

# Main and higher timeframe in seconds
MAIN_TIMEFRAME = 300        # 5 minutes
HIGHER_TIMEFRAME = 900      # 15 minutes

CANDLE_COUNT = 50

# ───────────────────────────
# Feature Toggles
# ───────────────────────────
USE_MULTI_TF = True         # Require both timeframes to agree
USE_FVG_FILTER = False       # Require Fair Value Gap in confluence
USE_SWING_FILTER = False     # Require Swing High/Low confluence

candles_main = []
candles_higher = []

# ───────────────────────────
# WebSocket Event Handlers
# ───────────────────────────
def on_open(ws):
    print("✅ Connected to Deriv WebSocket")
    ws.send(json.dumps({"authorize": DERIV_TOKEN}))

def on_message(ws, message):
    global candles_main, candles_higher
    data = json.loads(message)

    # ─── Authorization ───
    if "authorize" in data:
        print("🔑 Authorized successfully!")
        ws.send(json.dumps({
            "ticks_history": SYMBOL,
            "end": "latest",
            "count": CANDLE_COUNT,
            "style": "candles",
            "granularity": MAIN_TIMEFRAME,
            "subscribe": 1
        }))
        if USE_MULTI_TF:
            ws.send(json.dumps({
                "ticks_history": SYMBOL,
                "end": "latest",
                "count": CANDLE_COUNT,
                "style": "candles",
                "granularity": HIGHER_TIMEFRAME,
                "subscribe": 1
            }))

    elif "candles" in data:
        granularity = data["echo_req"]["granularity"]
        if granularity == MAIN_TIMEFRAME:
            candles_main = data["candles"]
        elif granularity == HIGHER_TIMEFRAME:
            candles_higher = data["candles"]
        process_strategy()

    elif "ohlc" in data:
        new_candle = data["ohlc"]
        granularity = data["echo_req"]["granularity"]

        if granularity == MAIN_TIMEFRAME:
            candles_main = update_candles(candles_main, new_candle)
        elif granularity == HIGHER_TIMEFRAME:
            candles_higher = update_candles(candles_higher, new_candle)

        process_strategy()

# ───────────────────────────
# Helper: Update Candle List
# ───────────────────────────
def update_candles(candle_list, new_candle):
    if candle_list and candle_list[-1]['epoch'] == new_candle['open_time']:
        candle_list[-1] = {
            "epoch": new_candle['open_time'],
            "open": new_candle['open'],
            "high": new_candle['high'],
            "low": new_candle['low'],
            "close": new_candle['close']
        }
    else:
        candle_list.append({
            "epoch": new_candle['open_time'],
            "open": new_candle['open'],
            "high": new_candle['high'],
            "low": new_candle['low'],
            "close": new_candle['close']
        })
        candle_list = candle_list[-CANDLE_COUNT:]
    return candle_list

# ───────────────────────────
# Main Strategy Logic
# ───────────────────────────
def process_strategy():
    if len(candles_main) < 14:
        return

    # Main TF
    close_main = [float(c["close"]) for c in candles_main]
    rsi_main = compute_rsi(close_main, 14)[-1]
    ema_main = compute_ema(close_main, 10)[-1]
    signal_main = get_signal(rsi_main, close_main[-1], ema_main)

    if USE_MULTI_TF:
        if len(candles_higher) < 14:
            return
        close_higher = [float(c["close"]) for c in candles_higher]
        rsi_higher = compute_rsi(close_higher, 14)[-1]
        ema_higher = compute_ema(close_higher, 10)[-1]
        signal_higher = get_signal(rsi_higher, close_higher[-1], ema_higher)
    else:
        signal_higher = signal_main

    print(f"📊 Main TF: {signal_main}, Higher TF: {signal_higher}")

    # Require both TFs to agree if enabled
    if USE_MULTI_TF and signal_main != signal_higher:
        print("⚪ MTF signals not aligned")
        return

    # Apply optional filters
    if USE_FVG_FILTER and not check_fvg(candles_main, signal_main):
        print("⚪ No matching FVG found")
        return
    if USE_SWING_FILTER and not check_swing_point(candles_main, signal_main):
        print("⚪ Swing point not favorable")
        return

    if signal_main == "BUY":
        print("🚀 BUY confirmed")
    elif signal_main == "SELL":
        print("🔻 SELL confirmed")

# ───────────────────────────
# Filters
# ───────────────────────────
def check_fvg(candles, direction):
    if len(candles) < 3:
        return False
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    if direction == "BUY":
        return float(c2["low"]) > float(c1["high"])
    elif direction == "SELL":
        return float(c2["high"]) < float(c1["low"])
    return False

def check_swing_point(candles, direction, lookback=3):
    if len(candles) < lookback * 2 + 1:
        return False
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    mid_idx = -lookback - 1
    if direction == "BUY":
        return lows[mid_idx] == min(lows[mid_idx - lookback: mid_idx + lookback + 1])
    elif direction == "SELL":
        return highs[mid_idx] == max(highs[mid_idx - lookback: mid_idx + lookback + 1])
    return False

# ───────────────────────────
# Indicators
# ───────────────────────────
def get_signal(rsi_value, close_price, ema_value):
    if rsi_value > 60 and close_price > ema_value:
        return "BUY"
    elif rsi_value < 40 and close_price < ema_value:
        return "SELL"
    return None

def compute_rsi(prices, period=14):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    rsi_values = []
    for i in range(period, len(prices)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi_values.append(100 - (100 / (1 + rs)))
    return [None] * period + rsi_values

def compute_ema(prices, period=10):
    ema_values = [sum(prices[:period]) / period]
    multiplier = 2 / (period + 1)
    for price in prices[period:]:
        ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
    return [None] * (period - 1) + ema_values

# ───────────────────────────
# Run WebSocket
# ───────────────────────────
if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}",
        on_open=on_open,
        on_message=on_message
    )
    ws.run_forever()
