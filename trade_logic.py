from typing import Dict, List, Optional, Any
import importlib

# Choose active strategy here
ACTIVE_STRATEGY = "strategies.scalper"   # or "strategies.momentum"

def evaluate_trades(last_price: float, open_trades: List[Dict], balance: float,
                    candles: List[Dict[str, float]], params: Optional[Dict[str, Any]]=None) -> Dict[str, Optional[float]]:
    strategy = importlib.import_module(ACTIVE_STRATEGY)
    return strategy.run_strategy(last_price, open_trades, balance, candles, params)
