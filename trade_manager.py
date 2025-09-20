# trading_manager.py
import logging
import importlib
from typing import Dict, Any, List
import numpy as np

import config
from utils import indicators
from risk_manager import RiskManager

# ───────────────────────────────
# Logging
# ───────────────────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class TradingManager:
    """Main manager to coordinate strategies and risk management."""

    def __init__(self):
        self.strategies: Dict[str, Any] = {}
        self.risk_manager = RiskManager()
        self.load_strategies()

    # ───────────────────────────────
    # Strategy loading
    # ───────────────────────────────
    def load_strategies(self):
        """Dynamically import and initialize all active strategies from config.py."""
        for strategy_name in config.ACTIVE_STRATEGIES:
            module_name = f"strategies.{strategy_name.lower()}"
            class_name = f"{strategy_name.upper()}_Strategy"

            try:
                module = importlib.import_module(module_name)
                StrategyClass = getattr(module, class_name)
                strategy_config = getattr(config, f"{strategy_name.upper()}_CONFIG", {})

                self.strategies[strategy_name] = StrategyClass(strategy_config)
                logger.info(f"✅ Loaded strategy: {strategy_name} with config: {strategy_config}")

            except Exception as e:
                logger.error(f"❌ Failed to load strategy {strategy_name}: {e}")

    # ───────────────────────────────
    # Indicator calculation
    # ───────────────────────────────
    def compute_indicators(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute common indicators once per cycle for efficiency."""
        closes = np.array([c["close"] for c in candles])
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])

        return indicators.calculate_common_indicators(
            highs=highs,
            lows=lows,
            closes=closes
        )

    # ───────────────────────────────
    # Core trading loop
    # ───────────────────────────────
    def run_cycle(self, candles: List[Dict[str, Any]], current_price: float) -> Dict[str, Any]:
        """
        Run a single decision cycle:
        - Compute indicators
        - Collect signals from all strategies
        - Filter through RiskManager
        - Execute valid trades
        """
        signals: Dict[str, Any] = {}
        ind = self.compute_indicators(candles)

        for name, strategy in self.strategies.items():
            # Step 1: Analyze market
            signal = strategy.analyze_market(candles, current_price, ind)
            signals[name] = signal

            action = signal.get("action", "").upper()
            if action in ["BUY", "SELL"]:
                # Step 2: Risk management checks
                stop_loss = config.get_strategy_stop_loss(name)
                account_balance = strategy.get_account_balance()
                position_size = self.risk_manager.get_position_size(
                    name, account_balance, stop_loss
                )

                if self.risk_manager.check_trade_allowed(
                    name,
                    potential_loss=position_size * stop_loss / 100
                ):
                    max_pos = config.get_max_open_positions(name)

                    # Step 3: Position limit check
                    if strategy.count_open_positions() < max_pos:
                        trade_result = strategy.execute_trade(
                            signal, current_price, position_size
                        )
                        self.risk_manager.record_trade_result(
                            name, trade_result.get("profit", 0)
                        )
                        logger.info(f"[{name}] ✅ Trade executed: {trade_result}")
                    else:
                        logger.warning(f"[{name}] 🚫 Max open positions reached ({max_pos}).")
                else:
                    logger.warning(f"[{name}] 🚫 Trade blocked by Risk Manager.")

            # Step 4: Manage existing positions
            strategy.manage_open_positions(current_price)

        return signals

    # ───────────────────────────────
    # Summary reporting
    # ───────────────────────────────
    def summary(self) -> Dict[str, Any]:
        """Return combined summary for all strategies."""
        return {
            name: strategy.get_account_summary()
            for name, strategy in self.strategies.items()
        }
