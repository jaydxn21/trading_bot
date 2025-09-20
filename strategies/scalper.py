# strategies/scalper.py
from typing import List, Dict, Any
from .base_strategies import BaseStrategy
from risk_manager import RiskManager


class Scalper_Strategy(BaseStrategy):
    """Simple scalping strategy using EMA crossovers."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("Scalper", config)

    def analyze_market(
        self, 
        candles: List[Dict[str, Any]], 
        price: float, 
        indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        ema_fast = indicators.get("ema_fast")
        ema_slow = indicators.get("ema_slow")

        signal = {"action": "HOLD", "reason": "No crossover"}

        if ema_fast is not None and ema_slow is not None:
            if ema_fast > ema_slow:
                signal = {"action": "BUY", "reason": f"EMA Fast ({ema_fast}) > EMA Slow ({ema_slow})"}
            elif ema_fast < ema_slow:
                signal = {"action": "SELL", "reason": f"EMA Fast ({ema_fast}) < EMA Slow ({ema_slow})"}

        return signal

    def execute_trade(self, signal: Dict[str, Any], price: float, position_size: float = None) -> Dict[str, Any]:
        """
        Execute trade using BaseStrategy to track stats and optionally attach position_size.
        """
        trade = super().execute_trade(signal, price, position_size)
        return trade

    def manage_open_positions(self, current_price: float):
        """
        Scalper-specific exit rules (tight SL/TP).
        For now, defer to BaseStrategy handling.
        """
        super().manage_open_positions(current_price)
