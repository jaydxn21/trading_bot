# quantum_github_pusher.py
import requests
import json
import time
import base64

# === CONFIG ===
GITHUB_TOKEN = "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"  # Generate at https://github.com/settings/tokens
REPO         = "jaydxn21/trading_bot"
FILE_PATH    = "signals.json"
BRANCH       = "main"

def send_signal(action, symbol="Volatility 100 Index", price=0, sl=0, tp=0):
    signal = {
        "action": action,
        "symbol": symbol,
        "price": price,
        "sl_price": sl,
        "tp_price": tp,
        "timestamp": int(time.time()) 
              }

    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Get current file SHA
    resp = requests.get(url, headers=headers)
    if resp.status_code == 404:
        sha = None
    else:
        sha = resp.json().get("sha")

    # Upload
    payload = {
        "message": f"Signal {action} {symbol}",
        "content": base64.b64encode(json.dumps(signal, indent=2).encode()).decode(),
        "branch": BRANCH
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=headers, json=payload)
    if r.status_code in (200, 201):
        print(f"SIGNAL SENT → {action} {symbol} at {time.strftime('%H:%M:%S')}")
    else:
        print("GitHub upload failed:", r.text)

# === TEST ===
if __name__ == "__main__":
    send_signal("BUY", "Volatility 100 Index", 100.500, 99.700, 101.300)