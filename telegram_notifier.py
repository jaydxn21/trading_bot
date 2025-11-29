# telegram_notifier.py
import requests
import logging
from typing import Dict, Any
from datetime import datetime
import config

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram notification system for trading signals"""
    
    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.enabled = config.TELEGRAM_ENABLED and self.bot_token and self.chat_id
        
        if self.enabled:
            logger.info("Telegram notifications ENABLED")
            self._test_connection()  # Optional: verify on startup
        else:
            logger.warning("Telegram notifications DISABLED - Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
    
    def _test_connection(self):
        """Send a test message on startup"""
        test_msg = "Bot Started\nTrading enabled\nR_100 Volatility Index"
        self.send_message(test_msg)
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram"""
        if not self.enabled:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message.strip(),
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.debug("Telegram notification sent")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    def format_exit_reason(self, exit_reason):
        """Format exit reason for readable display"""
        reason_map = {
            "take_profit": "Take Profit",
            "stop_loss": "Stop Loss", 
            "time_expiry": "Time Expiry",
            "manual_close": "Manual Close",
            "trailing_stop": "Trailing Stop",
            "signal_reversal": "Signal Reversal",
            "unknown": "Unknown"
        }
        return reason_map.get(exit_reason, "Unknown")
    
    def format_signal_message(self, signal_data: Dict[str, Any]) -> str:
        signal = signal_data.get("signal", "hold")
        if signal == "hold":
            return ""
        
        confidence = signal_data.get("confidence", 0)
        price = signal_data.get("price", 0)
        reason = signal_data.get("reason", "N/A")
        strategy = signal_data.get("strategy", "unknown")
        market_regime = signal_data.get("market_regime", "unknown")
        timestamp = signal_data.get("timestamp", datetime.now().strftime("%H:%M:%S"))
        
        emoji = "BUY" if signal == "buy" else "SELL"
        conf_emoji = "High" if confidence >= 70 else ("Medium" if confidence >= 50 else "Low")
        
        return f"""
{emoji} <b>NEW SIGNAL</b> {emoji}

<b>Signal:</b> {signal.upper()}
<b>Confidence:</b> {conf_emoji} {confidence}%
<b>Price:</b> ${price:.5f}
<b>Strategy:</b> {strategy}
<b>Regime:</b> {market_regime}

<i>Reason:</i> {reason}
<i>Time:</i> {timestamp}
""".strip()
    
    def format_trade_executed_message(self, trade_data: Dict[str, Any]) -> str:
        trade_type = trade_data.get("type", "buy").upper()
        entry = trade_data.get("entry_price", 0)
        sl = trade_data.get("sl", trade_data.get("stop_loss", 0))
        tp = trade_data.get("tp", trade_data.get("take_profit", 0))
        rr = trade_data.get("rr_ratio", trade_data.get("risk_reward_ratio", 0))
        conf = trade_data.get("confidence", 0)
        strategy = trade_data.get("strategy", "unknown")
        trade_id = trade_data.get("id", "N/A")
        
        return f"""
OPENED <b>TRADE #{trade_id}</b>

{trade_type} @ ${entry:.5f}
SL: ${sl:.5f}
TP: ${tp:.5f}
<b>R/R:</b> {rr:.1f}:1
<b>Conf:</b> {conf}%

<b>Strategy:</b> {strategy}
<i>Live on R_100</i>
""".strip()
    
    def format_trade_closed_message(self, trade_data: Dict[str, Any]) -> str:
        # FIX: Use exit_reason instead of close_reason
        direction = trade_data.get("direction", "buy").upper()
        entry = trade_data.get("entry_price", 0)
        exit_p = trade_data.get("exit_price", 0)
        pnl = trade_data.get("pnl", 0)
        pnl_pct = trade_data.get("pnl_percent", 0)
        
        # FIX: Get exit_reason and format it properly
        exit_reason = trade_data.get("exit_reason", "unknown")
        formatted_reason = self.format_exit_reason(exit_reason)
        
        strategy = trade_data.get("strategy", "unknown")
        trade_id = trade_data.get("id", "N/A")
        
        result = "PROFIT" if pnl > 0 else "LOSS"
        emoji = "✅" if pnl > 0 else "❌"
        
        return f"""
{emoji} CLOSED <b>TRADE #{trade_id}</b> — {result}

{direction} → Exit @ ${exit_p:.5f}
<b>P&L:</b> ${pnl:+.2f} ({pnl_pct:+.2f}%)
<b>Reason:</b> {formatted_reason}

<b>Strategy:</b> {strategy}
""".strip()
    
    def notify_signal(self, signal_data: Dict[str, Any]) -> bool:
        msg = self.format_signal_message(signal_data)
        return self.send_message(msg) if msg else False
    
    def notify_trade_executed(self, trade_data: Dict[str, Any]) -> bool:
        msg = self.format_trade_executed_message(trade_data)
        return self.send_message(msg)
    
    def notify_trade_closed(self, trade_data: Dict[str, Any]) -> bool:
        msg = self.format_trade_closed_message(trade_data)
        return self.send_message(msg)
    
    def notify_daily_summary(self, summary: Dict[str, Any]) -> bool:
        total = summary.get("total_trades", 0)
        wins = summary.get("wins", 0)
        loss = summary.get("losses", 0)
        pnl = summary.get("net_pnl", 0)
        win_rate = (wins / total * 100) if total > 0 else 0
        
        msg = f"""
DAILY REPORT

<b>Trades:</b> {total} | <b>Wins:</b> {wins} | <b>Losses:</b> {loss}
<b>Win Rate:</b> {win_rate:.1f}%
<b>Net P&L:</b> ${pnl:+.2f}

<i>Bot running smoothly on R_100</i>
""".strip()
        return self.send_message(msg)
    
    def notify_error(self, error: str, context: str = "") -> bool:
        msg = f"""
ALERT: BOT ERROR

<b>Error:</b> {error}
<b>Context:</b> {context}

<i>Check logs immediately</i>
""".strip()
        return self.send_message(msg)


# Global instance
telegram = TelegramNotifier()