from typing import List, Dict, Any
from .base_strategies import BaseStrategy


class SNR_ADX_Strategy(BaseStrategy):
    """Support & Resistance + ADX strategy."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("SNR_ADX", config)

    def analyze_market(
        self, 
        candles: List[Dict[str, Any]], 
        price: float, 
        indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        adx = indicators.get("adx", 0)
        support = indicators.get("support")
        resistance = indicators.get("resistance")

        signal = {"action": "HOLD", "reason": "No clear signal"}

        if adx >= self.config.get("min_adx", 20) and adx <= self.config.get("max_adx", 60):
            if support and price <= support:
                signal = {
                    "action": "BUY",
                    "reason": f"Price near support ({support}) with ADX={adx}"
                }
            elif resistance and price >= resistance:
                signal = {
                    "action": "SELL",
                    "reason": f"Price near resistance ({resistance}) with ADX={adx}"
                }

        return signal

    def execute_trade(
        self, 
        signal: Dict[str, Any], 
        price: float, 
        position_size: float
    ) -> Dict[str, Any]:
        """Execute trade with position sizing."""
        action = signal.get("action")
        if action in ["BUY", "SELL"]:
            trade = super().execute_trade(signal, price)
            if trade:
                trade["position_size"] = position_size
            return trade
        return None

    def manage_open_positions(self, current_price: float):
        """Optional: add strategy-specific exit rules."""
        super().manage_open_positions(current_price)
