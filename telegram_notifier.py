# telegram_notifier.py → FINAL FIXED & PYRIGHT/PYLANCE CLEAN (2025)

import requests
import logging
from typing import Dict, Any
from datetime import datetime
import threading           # ← THIS WAS MISSING
import time                # ← THIS WAS MISSING
import config

logger = logging.getLogger("Telegram")


class TelegramNotifier:
    def __init__(self):
        self.bot_token = getattr(config, "TELEGRAM_BOT_TOKEN", None)
        self.chat_id = getattr(config, "TELEGRAM_CHAT_ID", None)
        self.enabled = getattr(config, "TELEGRAM_ENABLED", False) and self.bot_token and self.chat_id
        
        if self.enabled:
            logger.info("Telegram notifications ENABLED")
            threading.Thread(target=self._send_startup_message, daemon=True).start()
        else:
            logger.warning("Telegram DISABLED — check config")

    def _send_startup_message(self):
        time.sleep(3)
        self.send_message("QuantumTrader PRO v7.4 Started\nMode: LIVE\nR_100 Volatility Index")

    def send_message(self, text: str) -> bool:
        if not self.enabled:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text.strip(),
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            r = requests.post(url, json=payload, timeout=10)
            if r.ok:
                return True
            else:
                logger.error(f"Telegram error: {r.status_code} {r.text}")
                return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    def format_exit_reason(self, reason: str) -> str:
        mapping = {
            "take_profit": "Take Profit",
            "stop_loss": "Stop Loss",
            "time_expiry": "Time Expiry",
            "manual_close": "Manual Close",
            "trailing_stop": "Trailing Stop",
            "signal_reversal": "Signal Reversal"
        }
        return mapping.get(reason, reason.title())

    def notify_signal(self, data: Dict[str, Any]) -> bool:
        s = data.get("signal", "").upper()
        if s not in ("BUY", "SELL"): 
            return False
        
        msg = f"""
NEW SIGNAL

<b>Direction:</b> {s}
<b>Price:</b> ${data.get('price', 0):.5f}
<b>Confidence:</b> {data.get('confidence', 0)}%
<b>Strategy:</b> {data.get('strategy', 'unknown')}

<i>{data.get('reason', 'AI Decision')}</i>
""".strip()
        return self.send_message(msg)

    def notify_trade_executed(self, data: Dict[str, Any]) -> bool:
        msg = f"""
TRADE OPENED #{data.get('id', 'N/A')}

<b>{data.get('type', 'CALL/PUT').upper()}</b> @ ${data.get('entry_price', 0):.5f}
<b>Strategy:</b> {data.get('strategy', 'unknown')}
<b>Confidence:</b> {data.get('confidence', 0)}%
""".strip()
        return self.send_message(msg)

    def notify_trade_closed(self, data: Dict[str, Any]) -> bool:
        pnl = data.get("pnl", 0)
        emoji = "PROFIT" if pnl > 0 else "LOSS"
        reason = self.format_exit_reason(data.get("exit_reason", "unknown"))
        
        msg = f"""
{emoji} TRADE CLOSED #{data.get('id', 'N/A')}

<b>P&L:</b> ${pnl:+.2f}
<b>Exit Reason:</b> {reason}
<b>Strategy:</b> {data.get('strategy', 'unknown')}
""".strip()
        return self.send_message(msg)

    def notify_error(self, title: str, details: str = "") -> bool:
        msg = f"""
BOT ERROR

<b>{title}</b>
{details}
<i>Immediate attention required</i>
""".strip()
        return self.send_message(msg)


# Global instance
telegram = TelegramNotifier()