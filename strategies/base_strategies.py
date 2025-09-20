# strategies/base_strategies.py
import logging
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class BaseStrategy:
    """
    Base class for all trading strategies.
    Handles trade tracking, stats, and position management.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.trade_count_today = 0
        self.last_trade_time = 0

        # Track open positions
        self.open_positions: List[Dict[str, Any]] = []

        # Daily performance stats
        self.daily_stats = {
            "trades_today": 0,
            "wins": 0,
            "losses": 0,
            "profit": 0.0,
            "loss": 0.0,
        }

    # ───────────────────────────────
    # Config
    # ───────────────────────────────
    def load_config(self, config: Dict[str, Any]):
        self.config.update(config)
        logger.info(f"[{self.name}] Config updated: {config}")

    # ───────────────────────────────
    # Core analysis logic
    # ───────────────────────────────
    def analyze_market(
        self, 
        candles: List[Dict[str, Any]], 
        price: float, 
        indicators: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Override this method in child strategies.
        Must return a dict like:
        {"action": "BUY"/"SELL"/"HOLD", "reason": "..."}
        """
        return {"action": "HOLD", "reason": "Base strategy does not generate signals"}

    # ───────────────────────────────
    # Trade execution
    # ───────────────────────────────
    def execute_trade(self, signal: Dict[str, Any], price: float, position_size: float = None) -> Optional[Dict[str, Any]]:
        """
        Logs and stores executed trades.
        Child classes may extend this to apply RiskManager.
        position_size is optional and added for modularity.
        """
        if signal.get("action") in ["BUY", "SELL"]:
            trade = {
                "strategy": self.name,
                "action": signal["action"],
                "price": price,
                "reason": signal.get("reason", ""),
                "time": time.time(),
                "stop_loss": self.config.get("stop_loss"),
                "take_profit": self.config.get("take_profit"),
                "status": "OPEN",
                "pnl": 0.0,
            }
            if position_size is not None:
                trade["position_size"] = position_size

            self.open_positions.append(trade)
            self.trade_count_today += 1
            self.daily_stats["trades_today"] += 1
            logger.info(f"[{self.name}] Trade opened: {trade}")
            return trade
        return None

    # ───────────────────────────────
    # Manage open positions
    # ───────────────────────────────
    def manage_open_positions(self, current_price: float):
        """
        Check SL/TP, update PnL, and close trades if conditions are met.
        """
        closed_positions = []
        for pos in self.open_positions[:]:
            direction = pos["action"]
            entry_price = pos["price"]
            sl = pos.get("stop_loss")
            tp = pos.get("take_profit")

            # Calculate PnL
            if direction == "BUY":
                pos["pnl"] = current_price - entry_price
            elif direction == "SELL":
                pos["pnl"] = entry_price - current_price

            # Stop Loss / Take Profit check
            if sl and ((direction == "BUY" and current_price <= sl) or (direction == "SELL" and current_price >= sl)):
                pos["status"] = "CLOSED"
                self.daily_stats["losses"] += 1
                self.daily_stats["loss"] += abs(pos["pnl"])
                closed_positions.append(pos)
                self.open_positions.remove(pos)
                logger.info(f"[{self.name}] Trade stopped out: {pos}")

            elif tp and ((direction == "BUY" and current_price >= tp) or (direction == "SELL" and current_price <= tp)):
                pos["status"] = "CLOSED"
                self.daily_stats["wins"] += 1
                self.daily_stats["profit"] += abs(pos["pnl"])
                closed_positions.append(pos)
                self.open_positions.remove(pos)
                logger.info(f"[{self.name}] Trade hit TP: {pos}")

        return closed_positions

    # ───────────────────────────────
    # Utilities
    # ───────────────────────────────
    def count_open_positions(self) -> int:
        return len(self.open_positions)

    def reset_daily_stats(self):
        self.trade_count_today = 0
        self.last_trade_time = 0
        self.open_positions = []
        self.daily_stats = {
            "trades_today": 0,
            "wins": 0,
            "losses": 0,
            "profit": 0.0,
            "loss": 0.0,
        }
        logger.info(f"[{self.name}] Daily stats reset")

    def get_account_summary(self) -> Dict[str, Any]:
        return {
            "strategy": self.name,
            "open_positions": len(self.open_positions),
            "stats": self.daily_stats,
        }
