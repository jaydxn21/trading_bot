import websocket
import json
import numpy as np

DERIV_TOKEN = "FscvuORyE062Izc"  # Replace with your real token
APP_ID = 96293
SYMBOL = "R_100"
TIMEFRAME = 60       # 1-minute candles
CANDLE_COUNT = 50

candles = []  # store latest candles

def on_open(ws):
    print("✅ Connected to Deriv WebSocket")
    ws.send(json.dumps({"authorize": DERIV_TOKEN}))

def on_message(ws, message):
    global candles
    data = json.loads(message)

    if "authorize" in data:
        print("🔑 Authorized successfully!")
        # Request historical candles
        ws.send(json.dumps({
            "ticks_history": SYMBOL,
            "end": "latest",
            "count": CANDLE_COUNT,
            "style": "candles",
            "granularity": TIMEFRAME,
            "subscribe": 1  # subscribe to updates
        }))

    elif "candles" in data:  # historical + first update
        candles = data["candles"]
        process_indicators()

    elif "ohlc" in data:  # live candle update
        new_candle = data["ohlc"]
        # Update last candle if same epoch, else append new one
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
            # Keep only last CANDLE_COUNT
            candles = candles[-CANDLE_COUNT:]

        process_indicators()

def process_indicators():
    close_prices = [float(c["close"]) for c in candles]
    if len(close_prices) < 14:  # Not enough data for RSI
        return

    rsi = compute_rsi(close_prices, 14)
    ema = compute_ema(close_prices, 10)

    print(f"📊 RSI: {rsi[-1]:.2f}, EMA: {ema[-1]:.2f}, Last Close: {close_prices[-1]}")

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

    return [None] * (period) + rsi_values

def compute_ema(prices, period=10):
    ema_values = [sum(prices[:period]) / period]
    multiplier = 2 / (period + 1)
    for price in prices[period:]:
        ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
    return [None] * (period - 1) + ema_values

if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        f"wss://ws.derivws.com/websockets/v3?app_id=96293",
        on_open=on_open,
        on_message=on_message
    )
    ws.run_forever()
