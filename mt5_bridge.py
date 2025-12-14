# mt5_bridge_v4_3.py — NO HMAC / STABLE

import json
import time
import base64
import requests
import logging
from typing import Dict, Any

# ============================================================
# CONFIG
# ============================================================
GITHUB_TOKEN = "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"
REPO = "jaydxn21/trading_bot"
FILE_PATH = "signals.json"
BRANCH = "main"

MAX_SIGNAL_AGE = 60
MAX_SIGNALS = 50

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MT5Bridge")

# ============================================================
# SESSION
# ============================================================
session = requests.Session()
session.headers.update({
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "QuantumTrader-MT5-Bridge-v4.3"
})

# ============================================================
# MAIN WRITE FUNCTION
# ============================================================
def write_signal(signal: Dict[str, Any]) -> bool:
    try:
        action = str(signal.get("action","")).upper()
        if action == "HOLD":
            return False

        ts = int(signal.get("timestamp",0))
        if abs(time.time() - ts) > MAX_SIGNAL_AGE:
            logger.warning("Signal too old")
            return False

        payload = {
            "action": action,
            "symbol": signal.get("symbol","R_100"),
            "price": float(signal.get("price",0.0)),
            "sl_price": signal.get("sl_price",""),
            "tp_price": signal.get("tp_price",""),
            "strategy": signal.get("strategy","manual"),
            "timestamp": str(ts)
        }

        url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
        resp = session.get(url)

        if resp.ok:
            sha = resp.json().get("sha")
            content = base64.b64decode(resp.json()["content"]).decode()
            signals = json.loads(content)
            if not isinstance(signals,list):
                signals=[]
        else:
            sha=None
            signals=[]

        signals.append(payload)
        signals = signals[-MAX_SIGNALS:]

        encoded = base64.b64encode(
            json.dumps(signals,separators=(",",":")).encode()
        ).decode()

        data = {
            "message": f"Add signal: {action} {payload['symbol']}",
            "content": encoded,
            "branch": BRANCH
        }
        if sha:
            data["sha"]=sha

        r = session.put(url,json=data,timeout=15)
        if r.status_code in (200,201):
            logger.info("MT5 BRIDGE → SUCCESS")
            return True

        logger.error(f"GitHub PUT failed: {r.status_code} {r.text}")
        return False

    except Exception as e:
        logger.error(f"Bridge error: {e}",exc_info=True)
        return False


class MT5Bridge:
    write_signal = staticmethod(write_signal)

mt5_bridge = MT5Bridge()
