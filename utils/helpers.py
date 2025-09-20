# utils/helpers.py
import json
import os
import time
from typing import List, Dict, Any

def load_json_config(file_path: str) -> dict:
    """Safely load a JSON config file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")
    with open(file_path, "r") as f:
        return json.load(f)

def timestamp() -> int:
    """Return current UTC timestamp as int."""
    return int(time.time())

# ───────────────────────────────
# Candle Creation & Updates
# ───────────────────────────────
def create_new_candle(tick: Dict[str, Any], timeframe: int = 60) -> Dict[str, Any]:
    """
    Create a new candle from a tick (price + timestamp).
    tick: {"epoch": timestamp, "quote": price}
    """
    ts = int(tick["epoch"])
    price = float(tick["quote"])
    candle_start = ts - (ts % timeframe)

    return {
        "timestamp": candle_start,
        "open": price,
        "high": price,
        "low": price,
        "close": price,
        "volume": 1,  # Always start with volume = 1
    }

def update_current_candle(candle: Dict[str, Any], tick: Dict[str, Any]) -> Dict[str, Any]:
    """Update the latest candle with a new tick."""
    price = float(tick["quote"])
    candle["high"] = max(candle["high"], price)
    candle["low"] = min(candle["low"], price)
    candle["close"] = price
    candle["volume"] = candle.get("volume", 0) + 1  # Always ensure volume exists
    return candle

def format_candles(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format candles for lightweight-charts (ensure `time` field exists)."""
    sorted_candles = sorted(candles, key=lambda x: x["timestamp"])
    formatted = []
    for c in sorted_candles:
        ts = int(c.get("timestamp", 0))
        # Convert ms → s if accidentally in ms
        if ts > 2000000000:
            ts = ts // 1000
        formatted.append({
            "time": ts,  # <-- required by lightweight-charts
            "open": round(c["open"], 5),
            "high": round(c["high"], 5),
            "low": round(c["low"], 5),
            "close": round(c["close"], 5),
            "volume": c.get("volume", 0),
        })
    return formatted

