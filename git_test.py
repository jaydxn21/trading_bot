import requests

token = "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"
url = "https://api.github.com/repos/jaydxn21/trading_bot/contents/signals.json"

r = requests.get(url, headers={"Authorization": f"token {token}"})
print(r.status_code, r.text)
