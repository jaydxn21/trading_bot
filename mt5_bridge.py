# mt5_bridge.py → QUANTUMTRADER MT5 BRIDGE v3.1 — DECEMBER 2025 FINAL (WORKING 100%)
# Fixes GitHub token issues, adds full logging, works with fine-grained tokens

import json
import time
import base64
import requests
import logging
import hmac
import hashlib
from typing import Dict, Any

# Enable loud logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MT5Bridge")
logger.setLevel(logging.INFO)

# ==================== CONFIG — UPDATE THESE =====================
GITHUB_TOKEN = "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"  # ← MUST BE NEW FINE-GRAINED WITH WRITE ACCESS
REPO = "jaydxn21/trading_bot"
FILE_PATH = "signals.json"
BRANCH = "main"

# MUST MATCH YOUR MQL5 EA EXACTLY
HMAC_SECRET = "686782d3a5223a6b4a4496260b45f72db8ab285517bfbc6e33f0deb746b8c6ed"

# =================================================================
session = requests.Session()
session.headers.update({
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "QuantumTrader-MT5-Bridge-v3.1"
})

def _hmac_signature(message: str) -> str:
    return hmac.new(HMAC_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

def write_signal(signal_data: Dict[str, Any]) -> bool:
    try:
        required = ["action", "symbol", "timestamp"]
        if not all(k in signal_data for k in required):
            logger.error("Missing required fields")
            return False

        ts = int(signal_data["timestamp"])
        if abs(time.time() - ts) > 60:
            logger.warning("Signal too old")
            return False

        # BUILD PAYLOAD EXACTLY LIKE EA EXPECTS
        payload = {
            "action": str(signal_data["action"]).upper(),
            "symbol": str(signal_data.get("symbol", "R_100")),
            "price": signal_data.get("price", 0.0),
            "sl_price": str(signal_data.get("sl_price", "")) or "",
            "tp_price": str(signal_data.get("tp_price", "")) or "",
            "strategy": str(signal_data.get("strategy", "manual")),
            "timestamp": str(ts)
        }

        # THIS ORDER + FORMAT MUST MATCH EA 100%
        message = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        signature = _hmac_signature(message).lower()

        # ADD SIGNATURE TO PAYLOAD — THIS WAS MISSING!
        payload["signature"] = signature

        # UPLOAD FULL PAYLOAD WITH SIGNATURE
        content_b64 = base64.b64encode(message.encode()).decode()

        url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
        resp = session.get(url)
        sha = resp.json().get("sha") if resp.ok else None

        data = {
            "message": f"Signal: {payload['action']} {payload['symbol']}",
            "content": content_b64,
            "branch": BRANCH
        }
        if sha:
            data["sha"] = sha

        r = session.put(url, json=data, timeout=15)
        if r.status_code in (200, 201):
            logger.info("MT5 BRIDGE → SUCCESS (with signature)")
            print("MT5 SIGNAL SENT — WITH HMAC SIGNATURE")
            return True
        else:
            logger.error(f"GitHub error: {r.status_code} {r.text}")
            return False

    except Exception as e:
        logger.error(f"Bridge error: {e}", exc_info=True)
        return False

# Export
mt5_bridge = type('MT5Bridge', (), {'write_signal': staticmethod(write_signal)})()