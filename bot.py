import websocket
import json
import numpy as np

DERIV_TOKEN = "FscvuORyE062Izc"  # Replace with your real token
APP_ID = 96293
SYMBOL = "R_100"
TIMEFRAME = 60       # 1-minute candles
CANDLE_COUNT = 50

candles = []  # store latest candles

# ───────────────────────────
# WebSocket Event Handlers
# ───────────────────────────
def on_open(ws):
    print("✅ Connected to Deriv WebSocket")
    ws.send(json.dumps({"authorize": DERIV_TOKEN}))

def on_message(ws, message):
    global candles
    data = json.loads(message)

    if "authorize" in data:
        print("🔑 Authorized successfully!")
        ws.send(json.dumps({
            "ticks_history": SYMBOL,
            "end": "latest",
            "count": CANDLE_COUNT,
            "style": "candles",
            "granularity": TIMEFRAME,
            "subscribe": 1
        }))

    elif "candles" in data:
        candles = data["candles"]
        process_indicators()

    elif "ohlc" in data:
        new_candle = data["ohlc"]
        if candles and candles[-1]['epoch'] == new_candle['open_time']:
            candles[-1] = {
                "epoch": new_candle['open_time'],
                "open": new_candle['open'],
                "high": new_candle['high'],
                "low": new_candle['low'],
                "close": new_candle['close']
            }
        else:
            candles.append({
                "epoch": new_candle['open_time'],
                "open": new_candle['open'],
                "high": new_candle['high'],
                "low": new_candle['low'],
                "close": new_candle['close']
            })
            candles = candles[-CANDLE_COUNT:]
        process_indicators()

# ───────────────────────────
# Indicator Processing
# ───────────────────────────
def process_indicators():
    close_prices = [float(c["close"]) for c in candles]
    if len(close_prices) < 14:
        return

    rsi = compute_rsi(close_prices, 14)
    ema = compute_ema(close_prices, 10)

    last_rsi = rsi[-1]
    last_ema = ema[-1]
    last_close = close_prices[-1]

    print(f"📊 RSI: {last_rsi:.2f}, EMA: {last_ema:.2f}, Last Close: {last_close}")

    # Signal verification
    if verify_signal(last_rsi, last_close, last_ema):
        if last_close > last_ema:
            print("🚀 BUY Signal Confirmed")
        elif last_close < last_ema:
            print("🔻 SELL Signal Confirmed")
    else:
        print("⚪ No valid signal")

# ───────────────────────────
# Signal Verification
# ───────────────────────────
def verify_signal(rsi_value, close_price, ema_value):
    # Example rule: RSI above 60 and price > EMA → BUY
    #               RSI below 40 and price < EMA → SELL
    if rsi_value > 60 and close_price > ema_value:
        return True
    elif rsi_value < 40 and close_price < ema_value:
        return True
    return False

# ───────────────────────────
# Indicator Calculations
# ───────────────────────────
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
