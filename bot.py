import websocket
import json
import numpy as np

DERIV_TOKEN = "FscvuORyE062Izc"
SYMBOL = "R_100"  # Change to your market (e.g., R_50, R_75)
TIMEFRAME = 60    # 1-minute candles
CANDLE_COUNT = 50

def on_open(ws):
    print("Connected to Deriv WebSocket")
    ws.send(json.dumps({"authorize": DERIV_TOKEN}))

def on_message(ws, message):
    data = json.loads(message)
    if "authorize" in data:
        print("Authorized successfully!")
        # Request historical candles
        ws.send(json.dumps({
            "ticks_history": SYMBOL,
            "end": "latest",
            "count": CANDLE_COUNT,
            "style": "candles",
            "granularity": TIMEFRAME
        }))

        ws.send(json.dumps({
    "ticks_history": SYMBOL,
    "style": "candles",
    "granularity": TIMEFRAME,
    "subscribe": 1
}))

    elif "candles" in data:
        candles = data["candles"]
        close_prices = [float(c["close"]) for c in candles]

        # Calculate RSI
        rsi = compute_rsi(close_prices, 14)
        ema = compute_ema(close_prices, 10)

        print(f"RSI: {rsi[-1]:.2f}, EMA: {ema[-1]:.2f}, Last Close: {close_prices[-1]}")

        # Example trade condition:
        if rsi[-1] < 30 and close_prices[-1] > ema[-1]:
            print("BUY signal")
        elif rsi[-1] > 70 and close_prices[-1] < ema[-1]:
            print("SELL signal")

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
        "wss://ws.derivws.com/websockets/v3?app_id=96293",
        on_open=on_open,
        on_message=on_message
    )
    ws.run_forever()
