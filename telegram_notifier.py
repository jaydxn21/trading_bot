# telegram_notifier.py — FINAL NUCLEAR EDITION 2025
import requests
import logging
from datetime import datetime

logger = logging.getLogger("Telegram")

# Global instance — used everywhere
telegram = None

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.enabled = os.getenv("TELEGRAM_ENABLED", "False").lower() == "true"
        self.enabled = self.enabled and self.bot_token and self.chat_id

        if self.enabled:
            logger.info("TELEGRAM NOTIFIER — NUCLEAR MODE ACTIVE")
            self.send("QuantumTrader PRO v8.1 STARTED\nNUKE MODE READY\nR_100 Live Signals")
        else:
            logger.warning("Telegram disabled — check .env")

    def send(self, text: str):
        if not self.enabled:
            return
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            requests.post(url, data={
                "chat_id": self.chat_id,
                "text": text.strip(),
                "parse_mode": "HTML"
            }, timeout=8)
        except:
            pass

    def notify_signal(self, data: dict):
        if not self.enabled:
            return
        s = data.get("signal", "").upper()
        if s not in ("BUY", "SELL"):
            return

        emoji = "BUY" if s == "BUY" else "SELL"
        msg = f"""
{s} {emoji} <b>NUCLEAR SIGNAL</b>

<b>Price:</b> {data.get('price', 0):.5f}
<b>Confidence:</b> {data.get('confidence', 0)}%
<b>Strategy:</b> {data.get('strategy', 'AI').upper()}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

{ 'NUKE MODE ACTIVE — 300+ TRADES/DAY' if os.getenv("NUKE_MODE", "false").lower() == "true" else "" }
        """.strip()
        self.send(msg)

# Create global instance
import os
telegram = TelegramNotifier()