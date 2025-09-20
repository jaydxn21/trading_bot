# historicalData.py
import json
import websocket
import threading
import time
from config import DERIV_WS_URL, API_TOKEN

def fetch_historical_candles(symbol=None, granularity=None, count=None, timeout=15):
    """
    Fetch historical candles from Deriv API via WebSocket.
    Returns a list of normalized candle dicts.
    """
    from config import SYMBOL, GRANULARITY, HISTORY_COUNT
    symbol = symbol or SYMBOL
    granularity = granularity or GRANULARITY
    count = count or HISTORY_COUNT

    candles_result = []
    done = threading.Event()
    ws_ref = [None]  # Store websocket reference to close it later

    def on_open(ws):
        print("[HistoricalWS] Connected. Authorizing...")
        ws.send(json.dumps({"authorize": API_TOKEN}))

    def on_message(ws, message):
        nonlocal candles_result
        try:
            data = json.loads(message)
            msg_type = data.get("msg_type")
            print(f"[HistoricalWS] Received: {msg_type}")

            if msg_type == "authorize":
                # Request historical candles
                request = {
                    "ticks_history": symbol,
                    "end": "latest",
                    "count": count,
                    "granularity": granularity,
                    "style": "candles"
                }
                print(f"[HistoricalWS] Sending request: {request}")
                ws.send(json.dumps(request))

            elif msg_type == "candles" or msg_type == "history":
                # Deriv sometimes returns 'history' instead of 'candles'
                candles_result = data.get("candles", []) or data.get("history", [])
                # Normalize
                for c in candles_result:
                    if "epoch" in c and "timestamp" not in c:
                        c["timestamp"] = c["epoch"]
                print(f"[HistoricalWS] Got {len(candles_result)} candles")
                done.set()
                ws.close()

            elif msg_type == "error":
                error_msg = data.get("error", {}).get("message", "Unknown error")
                print(f"[HistoricalWS] Error: {error_msg}")
                done.set()
                ws.close()
                
        except Exception as e:
            print(f"[HistoricalWS] Error processing message: {e}")
            done.set()

    def on_error(ws, error):
        print(f"[HistoricalWS] WebSocket error: {error}")
        done.set()

    def on_close(ws, close_status_code, close_msg):
        print("[HistoricalWS] WebSocket connection closed")

    ws = websocket.WebSocketApp(
        DERIV_WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    ws_ref[0] = ws

    thread = threading.Thread(target=ws.run_forever, daemon=True)
    thread.start()

    finished = done.wait(timeout)
    if not finished:
        print("[HistoricalWS] Timeout: No data received")
        if ws_ref[0]:
            try:
                ws_ref[0].close()
            except:
                pass

    return candles_result