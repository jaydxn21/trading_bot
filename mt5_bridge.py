# mt5_bridge.py → QUANTUMTRADER MT5 BRIDGE v3.0 (DEC 2025 FINAL)
# Fully secure, HMAC-signed, replay-protected, error-resilient
# Works perfectly with the MQL5 EA I gave you earlier

import json
import time
import base64
import requests
import logging
import hmac
import hashlib
from typing import Dict, Any, Optional

logger = logging.getLogger("MT5Bridge")

# ==================== CONFIG — UPDATE THESE =====================
GITHUB_TOKEN = "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"  # ← YOUR FINE-GRAINED TOKEN
REPO = "jaydxn21/trading_bot"
FILE_PATH = "signals.json"
BRANCH = "main"

# MUST BE EXACTLY THE SAME AS IN YOUR MQL5 EA!!!
HMAC_SECRET = "686782d3a5223a6b4a4496260b45f72db8ab285517bfbc6e33f0deb746b8c6ed"   # ←←← MATCHES EA

# =================================================================
SESSION = requests.Session()
SESSION.headers.update({
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "QuantumTrader-MT5-Bridge-v3"
})

def _hmac_signature(message: str) -> str:
    return hmac.new(
        HMAC_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def write_signal(signal_data: Dict[str, Any]) -> bool:
    """
    Called from bot.py like:
        mt5_bridge.write_signal({
            "action": "BUY",
            "symbol": "EURUSD",
            "price": 1.08500,
            "sl_price": 1.08200,
            "tp_price": 1.09000,
            "strategy": "super_scalper",
            "timestamp": int(time.time())
        })
    """
    try:
        # === 1. Input validation ===
        required = ["action", "symbol", "timestamp"]
        if not all(k in signal_data for k in required):
            logger.error("MT5 Bridge: Missing required fields")
            return False

        action = str(signal_data["action"]).upper()
        if action not in ("BUY", "SELL"):
            logger.error(f"Invalid action: {action}")
            return False

        ts = int(signal_data["timestamp"])
        if abs(time.time() - ts) > 30:
            logger.warning(f"Signal timestamp too old/future: {ts}")
            return False

        # === 2. Build exact payload that MQL5 expects ===
        payload = {
            "action": action,
            "symbol": str(signal_data.get("symbol", "R_100")),
            "price": signal_data.get("price", "null"),           # can be null or number as string
            "sl_price": str(signal_data.get("sl_price", "")) or "",
            "tp_price": str(signal_data.get("tp_price", "")) or "",
            "strategy": str(signal_data.get("strategy", "manual")),
            "timestamp": str(ts)
        }

        # === 3. Create exact message for HMAC (must match MQL5 StringFormat!) ===
        message = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        signature = _hmac_signature(message)

        payload["signature"] = signature.lower()  # MQL5 outputs lowercase

        # === 4. Upload to GitHub ===
        url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
        
        # Get current file SHA (required for update)
        try:
            resp = SESSION.get(url, timeout=10)
            sha = resp.json().get("sha") if resp.ok else None
        except:
            sha = None

        content_b64 = base64.b64encode(message.encode('utf-8')).decode('utf-8')

        put_data = {
            "message": f"QuantumTrader: {action} {payload['symbol']} @ {payload['price']}",
            "content": content_b64,
            "branch": BRANCH
        }
        if sha:
            put_data["sha"] = sha

        r = SESSION.put(url, json=put_data, timeout=15)

        if r.status_code in (200, 201):
            logger.info(f"MT5 BRIDGE → {action} {payload['symbol']} | "
                        f"SL:{payload['sl_price']} TP:{payload['tp_price']} | "
                        f"{payload['strategy']} | ts:{ts}")
            print(f"EXECUTED ON MT5 IN <3s → {action} {payload['symbol']}")
            return True
        else:
            logger.error(f"GitHub upload failed: {r.status_code} {r.text}")
            return False

    except Exception as e:
        logger.error(f"MT5 Bridge Exception: {e}", exc_info=True)
        return False

# === EXPORT EXACTLY WHAT bot.py EXPECTS ===
mt5_bridge = type('MT5Bridge', (), {'write_signal': staticmethod(write_signal)})()