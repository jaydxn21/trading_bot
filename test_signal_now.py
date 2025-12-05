# test_signal_now.py — FINAL SIGNED VERSION (DEC 2025)
import json
import time
import base64
import requests
import hmac
import hashlib

GITHUB_TOKEN = "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"
REPO = "jaydxn21/trading_bot"
FILE_PATH = "signals.json"
BRANCH = "main"
HMAC_SECRET = "686782d3a5223a6b4a4496260b45f72db8ab285517bfbc6e33f0deb746b8c6ed"

def send_signed_signal():
    ts = int(time.time())
    payload = {
        "action": "BUY",
        "symbol": "Volatility 100 Index",
        "price": "100.5",
        "sl_price": "99.7",
        "tp_price": "101.3",
        "strategy": "test",
        "timestamp": str(ts)
    }
    message = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    signature = hmac.new(HMAC_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest().lower()
    payload["signature"] = signature

    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    resp = requests.get(url, headers=headers)
    sha = resp.json().get("sha") if resp.status_code == 200 else None

    content = base64.b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode()
    data = {"message": "TEST SIGNAL", "content": content, "branch": BRANCH}
    if sha: data["sha"] = sha

    r = requests.put(url, headers=headers, json=data)
    if r.status_code in (200, 201):
        print(f"SIGNAL SENT AND SIGNED @ {time.strftime('%H:%M:%S')}")
        print("MT5 WILL EXECUTE IN <3s → CHECK EXPERTS TAB NOW")
    else:
        print("Failed:", r.text)

if __name__ == "__main__":
    send_signed_signal()