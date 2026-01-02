# mt5_bridge.py — Multi-Symbol Production-Safe GitHub MT5 Signal Bridge

import json
import time
import base64
import logging
import requests
import os
from typing import Dict, Any

# ─────────────────────────────────────────────
# CONFIG
REPO = "jaydxn21/trading_bot"
BRANCH = "main"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # REQUIRED

MAX_SIGNAL_AGE = 20        # seconds
DEDUP_WINDOW = 5           # seconds
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10

# ─────────────────────────────────────────────
# SYMBOL → FILE MAPPING (CRITICAL FOR MULTI-EA)
SYMBOL_FILES = {
    "Volatility 100 Index": "signals/v100.json",
    "Crash 1000 Index": "signals/crash1000.json",
    "Boom 1000 Index": "signals/boom1000.json",
}

# ─────────────────────────────────────────────
logger = logging.getLogger("MT5Bridge")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

_last_sent_signature = {}
_last_sent_time = {}

# ─────────────────────────────────────────────
def _github_headers() -> Dict[str, str]:
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN not set")

    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "QuantumTrader-MT5Bridge/2.0",
    }

# ─────────────────────────────────────────────
def _get_remote_file(path: str):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"

    r = requests.get(
        url,
        headers=_github_headers(),
        timeout=REQUEST_TIMEOUT
    )

    if r.status_code == 404:
        return [], None

    if r.status_code != 200:
        logger.error(f"GitHub API error {r.status_code}: {r.text}")
        return [], None

    body = r.json()

    try:
        content = base64.b64decode(body["content"]).decode("utf-8")
        data = json.loads(content)
    except Exception as e:
        logger.error(f"Failed to decode {path}: {e}")
        return [], body.get("sha")

    if not isinstance(data, list):
        data = []

    return data, body.get("sha")

# ─────────────────────────────────────────────
def _push_file(path: str, data: list, sha: str | None):
    raw = json.dumps(data, indent=2)
    encoded = base64.b64encode(raw.encode("utf-8")).decode("utf-8")

    payload = {
        "message": "MT5 trade signal",
        "content": encoded,
        "branch": BRANCH,
    }

    if sha:
        payload["sha"] = sha

    url = f"https://api.github.com/repos/{REPO}/contents/{path}"

    r = requests.put(
        url,
        headers=_github_headers(),
        json=payload,
        timeout=REQUEST_TIMEOUT
    )

    if r.status_code not in (200, 201):
        raise RuntimeError(
            f"GitHub push failed {r.status_code}: {r.text}"
        )

# ─────────────────────────────────────────────
def write_signal(signal: Dict[str, Any], attempt: int = 0) -> bool:
    try:
        action = str(signal.get("action", "")).upper()
        if action not in ("BUY", "SELL"):
            return False

        symbol = signal.get("symbol")
        if symbol not in SYMBOL_FILES:
            logger.warning(f"Symbol not mapped → {symbol}")
            return False

        ts = signal.get("timestamp")
        if not isinstance(ts, int):
            ts = int(time.time())

        now = int(time.time())
        age = abs(now - ts)

        if age > MAX_SIGNAL_AGE:
            logger.warning(f"{symbol} signal too old — dropped ({age}s)")
            return False

        signature = f"{action}:{symbol}:{ts}"

        if (
            signature == _last_sent_signature.get(symbol)
            and now - _last_sent_time.get(symbol, 0) < DEDUP_WINDOW
        ):
            logger.info(f"{symbol} duplicate signal suppressed")
            return False

        payload = {
            "action": action,
            "symbol": symbol,
            "confidence": int(signal.get("confidence", 0)),
            "strategy": signal.get("strategy", "manual"),
            "timestamp": ts,
        }

        path = SYMBOL_FILES[symbol]
        data, sha = _get_remote_file(path)
        data.append(payload)

        _push_file(path, data, sha)

        _last_sent_signature[symbol] = signature
        _last_sent_time[symbol] = now

        logger.info(f"MT5 BRIDGE → {symbol} SIGNAL SENT")
        return True

    except Exception as e:
        logger.error(f"MT5 BRIDGE ERROR: {e}")

        if attempt < MAX_RETRIES:
            time.sleep(1)
            return write_signal(signal, attempt + 1)

        return False

# ─────────────────────────────────────────────
def has_open_position() -> bool:
    """
    Stub for compatibility.
    MT5 EAs manage real positions.
    """
    return False
