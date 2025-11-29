# telebot.py
import logging
import requests
from typing import Dict, Any
import config

logger = logging.getLogger(__name__)

def _send_telegram(message: str):
    if not config.TELEGRAM_ENABLED:
        return
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram disabled: missing token or chat_id")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")

def notify_signal(data: Dict):
    msg = (
        f"<b>SIGNAL</b>\n"
        f"Strategy: {data['strategy']}\n"
        f"Action: {data['signal'].upper()}\n"
        f"Confidence: {data['confidence']:.1f}%\n"
        f"Price: ${data['price']:.5f}\n"
        f"Time: {data['timestamp']}"
    )
    _send_telegram(msg)

def notify_trade_executed(data: Dict):
    msg = (
        f"<b>TRADE EXECUTED</b>\n"
        f"ID: <code>{data['id']}</code>\n"
        f"Type: {data['type'].upper()}\n"
        f"Entry: ${data['entry_price']:.5f}\n"
        f"Strategy: {data['strategy']}\n"
        f"Confidence: {data.get('confidence', 75):.1f}%"
    )
    _send_telegram(msg)

def notify_trade_closed(data: Dict):
    pnl = data['pnl']
    color = "WIN" if pnl > 0 else "LOSS"
    msg = (
        f"<b>TRADE CLOSED {color}</b>\n"
        f"ID: <code>{data['id']}</code>\n"
        f"PnL: ${pnl:+.2f} ({data['pnl_percent']:+.1f}%)\n"
        f"Entry: ${data['entry_price']:.5f} to Exit: ${data['exit_price']:.5f}\n"
        f"Reason: {data['close_reason']}\n"
        f"Strategy: {data['strategy']}"
    )
    _send_telegram(msg)

def notify_error(title: str, details: str):
    msg = f"<b>ERROR: {title}</b>\n<pre>{details}</pre>"
    _send_telegram(msg)

def notify_system_status(title: str, details: str):
    msg = f"<b>{title}</b>\n{details}"
    _send_telegram(msg)

def notify_daily_summary(data: Dict):
    msg = (
        f"<b>DAILY SUMMARY</b>\n"
        f"Total Trades: {data['total_trades']}\n"
        f"Wins: {data['wins']} | Losses: {data['losses']}\n"
        f"Net PnL: ${data['net_pnl']:+.2f}"
    )
    _send_telegram(msg)

# ADD THIS AT THE END
telegram = type('Telegram', (), {
    'notify_signal': notify_signal,
    'notify_trade_executed': notify_trade_executed,
    'notify_trade_closed': notify_trade_closed,
    'notify_error': notify_error,
    'notify_system_status': notify_system_status,
    'notify_daily_summary': notify_daily_summary,
})