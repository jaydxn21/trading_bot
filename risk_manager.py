# risk_manager.py
import logging
import config

logger = logging.getLogger(__name__)


class RiskManager:
    """Centralized risk management for multi-strategy trading."""

    def __init__(self):
        # Track trades, losses, recovery state per strategy
        self.strategy_state = {
            name: {
                "daily_loss": 0.0,
                "consecutive_losses": 0,
                "recovery_mode": False,
            }
            for name in config.ACTIVE_STRATEGIES
        }

    def check_trade_allowed(self, strategy_name: str, potential_loss: float) -> bool:
        """Return True if trade is allowed based on risk limits."""
        state = self.strategy_state[strategy_name]
        max_daily_loss = config.get_strategy_daily_loss(strategy_name)

        if state["recovery_mode"]:
            logger.warning(f"[{strategy_name}] Recovery mode active. Trade skipped.")
            return False

        if (state["daily_loss"] + potential_loss) > max_daily_loss:
            logger.warning(f"[{strategy_name}] Max daily loss reached. Activating recovery mode.")
            state["recovery_mode"] = True
            return False

        return True

    def record_trade_result(self, strategy_name: str, profit: float):
        """Update consecutive losses, daily loss, and recovery mode after trade."""
        state = self.strategy_state[strategy_name]

        if profit < 0:
            state["consecutive_losses"] += 1
            state["daily_loss"] += abs(profit)
        else:
            state["consecutive_losses"] = 0
            state["daily_loss"] -= profit  # optional, can ignore for gain

        # Activate recovery mode if too many consecutive losses
        if state["consecutive_losses"] >= config.MAX_CONSECUTIVE_LOSSES:
            state["recovery_mode"] = True
            logger.warning(f"[{strategy_name}] Max consecutive losses reached. Recovery mode activated.")

    def reset_daily(self, strategy_name: str):
        """Reset daily tracking (call at start of new trading day)."""
        state = self.strategy_state[strategy_name]
        state["daily_loss"] = 0.0
        state["consecutive_losses"] = 0
        state["recovery_mode"] = False

    def get_position_size(self, strategy_name: str, account_balance: float, stop_loss_percent: float) -> float:
        """Calculate position size based on risk per trade and stop loss."""
        risk = config.get_strategy_risk(strategy_name)
        position_size = (account_balance * risk) / (stop_loss_percent / 100)
        return position_size
