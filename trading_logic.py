import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class TradingLogic:
    def __init__(self, starting_balance: float = 1000.0, risk_per_trade: float = 0.02):
        self.balance = starting_balance
        self.equity = starting_balance
        self.risk_per_trade = risk_per_trade
        self.positions: List[Dict[str, Any]] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.position_id_counter = 0

    # ───────────────────────────────
    # Risk Management
    # ───────────────────────────────
    def calculate_position_size(self, stop_distance: float, price: float) -> float:
        if stop_distance <= 0:
            return 0
        risk_amount = self.balance * self.risk_per_trade
        size = risk_amount / stop_distance
        return round(size, 4)

    # ───────────────────────────────
    # Trade Execution
    # ───────────────────────────────
    def open_position(
        self,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        strategy: str,
        trade_cost: float = 0.0,
    ) -> Optional[int]:
        size = self.calculate_position_size(abs(entry_price - stop_loss), entry_price)
        if size <= 0:
            logger.warning("❌ Invalid position size. Trade skipped.")
            return None

        self.position_id_counter += 1
        pos = {
            "id": self.position_id_counter,
            "direction": direction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "size": size,
            "strategy": strategy,
            "opened_at": datetime.utcnow(),
            "trade_cost": trade_cost,
        }
        self.positions.append(pos)
        logger.info(f"📈 Opened {direction.upper()} #{pos['id']} | Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}, Size: {size}")
        return pos["id"]

    def close_position(self, pos_id: int, exit_price: float, reason: str) -> Optional[float]:
        pos = next((p for p in self.positions if p["id"] == pos_id), None)
        if not pos:
            return None

        if pos["direction"] == "buy":
            pnl = (exit_price - pos["entry_price"]) * pos["size"]
        else:
            pnl = (pos["entry_price"] - exit_price) * pos["size"]

        pnl -= pos.get("trade_cost", 0)
        self.balance += pnl
        self.equity = self.balance

        self.positions = [p for p in self.positions if p["id"] != pos_id]

        trade_record = {
            "id": pos_id,
            "direction": pos["direction"],
            "entry_price": pos["entry_price"],
            "exit_price": exit_price,
            "stop_loss": pos["stop_loss"],
            "take_profit": pos["take_profit"],
            "size": pos["size"],
            "strategy": pos["strategy"],
            "opened_at": pos["opened_at"],
            "closed_at": datetime.utcnow(),
            "exit_reason": reason,
            "profit_loss": pnl,
            "trade_cost": pos.get("trade_cost", 0),
        }
        self.trade_history.append(trade_record)
        logger.info(f"📉 Closed {pos['direction'].upper()} #{pos_id} | Exit: {exit_price}, PnL: {pnl:.2f}, Reason: {reason}")
        return pnl

    # ───────────────────────────────
    # Position Management
    # ───────────────────────────────
    def manage_open_positions(self, current_price: float):
        closed_positions = []

        for pos in list(self.positions):
            # --- Take Profit hit ---
            if (pos["direction"] == "buy" and current_price >= pos["take_profit"]) or \
               (pos["direction"] == "sell" and current_price <= pos["take_profit"]):
                pnl = self.close_position(pos["id"], current_price, "Take profit")
                if pnl is not None:
                    closed_positions.append({"id": pos["id"], "reason": "Take profit", "pnl": pnl})
                continue

            # --- Stop Loss hit ---
            if (pos["direction"] == "buy" and current_price <= pos["stop_loss"]) or \
               (pos["direction"] == "sell" and current_price >= pos["stop_loss"]):
                pnl = self.close_position(pos["id"], current_price, "Stop hit")
                if pnl is not None:
                    closed_positions.append({"id": pos["id"], "reason": "Stop hit", "pnl": pnl})
                continue

            # --- Break-even logic ---
            rr_halfway = abs(pos["take_profit"] - pos["entry_price"]) / 2
            if pos["direction"] == "buy" and current_price >= pos["entry_price"] + rr_halfway:
                new_sl = max(pos["stop_loss"], pos["entry_price"])
                if new_sl != pos["stop_loss"]:
                    pos["stop_loss"] = new_sl
                    logger.info(f"🔒 Break-even stop set for BUY #{pos['id']} at {new_sl:.2f}")

            if pos["direction"] == "sell" and current_price <= pos["entry_price"] - rr_halfway:
                new_sl = min(pos["stop_loss"], pos["entry_price"])
                if new_sl != pos["stop_loss"]:
                    pos["stop_loss"] = new_sl
                    logger.info(f"🔒 Break-even stop set for SELL #{pos['id']} at {new_sl:.2f}")

        return closed_positions

    # ───────────────────────────────
    # Performance Analysis
    # ───────────────────────────────
    def analyze_performance(self) -> Dict[str, Any]:
        if not self.trade_history:
            return {"message": "No trades yet", "total_trades": 0, "win_rate": 0}

        wins = [t for t in self.trade_history if t.get("profit_loss", 0) > 0]
        losses = [t for t in self.trade_history if t.get("profit_loss", 0) <= 0]
        total_trades = len(self.trade_history)
        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
        avg_win = sum(t["profit_loss"] for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(t["profit_loss"] for t in losses) / len(losses) if losses else 0.0
        total_profit = sum(t["profit_loss"] for t in self.trade_history)
        total_trade_costs = sum(t.get("trade_cost", 0) for t in self.trade_history)

        exit_reasons = {}
        for t in self.trade_history:
            r = t.get("exit_reason", "Unknown")
            exit_reasons[r] = exit_reasons.get(r, 0) + 1

        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "wins": len(wins),
            "losses": len(losses),
            "average_win": avg_win,
            "average_loss": avg_loss,
            "total_profit": total_profit,
            "trade_costs": total_trade_costs,
            "net_profit_after_costs": total_profit - total_trade_costs,
            "exit_reasons": exit_reasons,
            "final_balance": self.balance,
            "final_equity": self.equity,
        }
