# strategies/sma.py
from typing import List, Dict, Any
from .base_strategies import BaseStrategy

class SMA_Strategy(BaseStrategy):
    """Simple Moving Average crossover strategy."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("SMA", config)

    def analyze_market(self, candles: List[Dict[str, Any]], price: float, indicators: Dict[str, Any]) -> Dict[str, Any]:
        sma_fast = indicators.get("sma_fast")
        sma_slow = indicators.get("sma_slow")

        signal = {"action": "HOLD", "reason": "No crossover"}

        if sma_fast is not None and sma_slow is not None:
            if sma_fast > sma_slow:
                signal = {"action": "BUY", "reason": "Fast SMA above Slow SMA"}
            elif sma_fast < sma_slow:
                signal = {"action": "SELL", "reason": "Fast SMA below Slow SMA"}

        return signal

    def execute_trade(self, signal: Dict[str, Any], price: float) -> Dict[str, Any]:
        if signal["action"] in ["BUY", "SELL"]:
            return {
                "strategy": self.name,
                "action": signal["action"],
                "price": price,
                "reason": signal["reason"]
            }
        return None
