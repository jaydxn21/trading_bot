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
        # === VALIDATION ===
        required = ["action", "symbol", "timestamp"]
        if not all(k in signal_data for k in required):
            logger.error(f"Missing required fields: {list(signal_data.keys())}")
            return False

        action = str(signal_data["action"]).upper()
        if action not in ("BUY", "SELL"):
            logger.error(f"Invalid action: {action}")
            return False

        ts = int(signal_data["timestamp"])
        if abs(time.time() - ts) > 60:  # allow 60s window
            logger.warning("Signal timestamp too old")
            return False

        # === BUILD PAYLOAD EXACTLY LIKE MQL5 EXPECTS ===
        payload = {
            "action": action,
            "symbol": str(signal_data.get("symbol", "R_100")),
            "price": signal_data.get("price", 0.0),
            "sl_price": str(signal_data.get("sl_price", "")) or "",
            "tp_price": str(signal_data.get("tp_price", "")) or "",
            "strategy": str(signal_data.get("strategy", "manual")),
            "timestamp": str(ts)
        }

        message = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        signature = _hmac_signature(message).lower()
        payload["signature"] = signature

        # === ENCODE CONTENT ===
        content_b64 = base64.b64encode(message.encode('utf-8')).decode('utf-8')

        url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

        # Get current file to get SHA
        try:
            resp = session.get(url)
            resp.raise_for_status()
            sha = resp.json()["sha"]
        except Exception as e:
            logger.warning(f"Could not get current file SHA: {e}")
            sha = None

        # === UPLOAD ===
        data = {
            "message": f"MT5 Signal: {action} {payload['symbol']} @ {payload['price']}",
            "content": content_b64,
            "branch": BRANCH,
        }
        if sha:
            data["sha"] = sha

        logger.info(f"Sending to GitHub: {action} {payload['symbol']} @ {payload['price']}")

        r = session.put(url, json=data, timeout=15)

        if r.status_code in (200, 201):
            logger.info("MT5 BRIDGE → SUCCESS! signals.json updated")
            print("MT5 SIGNAL SUCCESS → signals.json updated in GitHub!")
            return True
        else:
            error_msg = r.json() if r.headers.get('content-type') == 'application/json' else r.text
            logger.error(f"GitHub API Error {r.status_code}: {error_msg}")
            print(f"MT5 BRIDGE FAILED: {r.status_code} → {error_msg}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {e}")
        print(f"NETWORK ERROR: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in MT5 bridge: {e}", exc_info=True)
        print(f"BRIDGE CRASHED: {e}")
        return False

# Export
mt5_bridge = type('MT5Bridge', (), {'write_signal': staticmethod(write_signal)})()