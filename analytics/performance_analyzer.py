# analytics/performance_analyzer.py
import requests
import json
from collections import defaultdict

class PerformanceAnalyzer:
    def __init__(self, journal_endpoint=None):
        self.journal_endpoint = journal_endpoint or "http://127.0.0.1:8085/journal"
        self.journal_data = []

    # ---------------------------------------------------------
    def load(self):
        """Fetch journal events from EA endpoint"""
        try:
            response = requests.get(self.journal_endpoint, timeout=5)
            response.raise_for_status()
            self.journal_data = json.loads(response.text)
            print(f"Loaded {len(self.journal_data)} journal events.")
        except Exception as e:
            raise RuntimeError(f"Failed to load journal: {e}")

    # ---------------------------------------------------------
    def analyze(self):
        """Compute performance metrics from journal"""
        if not self.journal_data:
            print("No journal data loaded.")
            return [], {}

        trades = defaultdict(lambda: {
            "entry": None,
            "exit": None,
            "partials": []
        })

        # ------------------ GROUP EVENTS ------------------
        for evt in self.journal_data:
            ticket = evt.get("ticket")
            evt_type = evt.get("event")

            if not ticket or not evt_type:
                continue

            if evt_type == "ENTRY":
                trades[ticket]["entry"] = {
                    "price": float(evt.get("price", 0)),
                    "volume": float(evt.get("volume", 0)),
                    "time": evt.get("time"),
                    "confidence": evt.get("confidence"),
                    "strategy": evt.get("strategy"),
                }

            elif evt_type in ("CLOSE_PROFIT", "CLOSE_LOSS"):
                trades[ticket]["exit"] = {
                    "profit": float(evt.get("profit", 0)),
                    "time": evt.get("time"),
                    "type": evt_type
                }

            elif evt_type == "PARTIAL_CLOSE":
                trades[ticket]["partials"].append({
                    "price": float(evt.get("price", 0)),
                    "volume": float(evt.get("volume", 0)),
                    "time": evt.get("time")
                })

        # ------------------ ANALYZE ------------------
        results = []
        total_profit = 0.0
        wins = 0
        losses = 0

        for ticket, trade in trades.items():
            entry = trade["entry"]
            exit_ = trade["exit"]

            # strict lifecycle enforcement
            if not entry or not exit_:
                continue

            profit = exit_["profit"]
            total_profit += profit

            if profit > 0:
                wins += 1
            elif profit < 0:
                losses += 1

            results.append({
                "ticket": ticket,
                "entry_time": entry["time"],
                "exit_time": exit_["time"],
                "strategy": entry.get("strategy"),
                "confidence": entry.get("confidence"),
                "profit": round(profit, 5),
                "partials": len(trade["partials"])
            })

        total_trades = wins + losses
        winrate = (wins / total_trades * 100) if total_trades else 0.0

        summary = {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "winrate": round(winrate, 2),
            "total_profit": round(total_profit, 5)
        }

        # ------------------ OUTPUT ------------------
        print("\nPerformance Summary")
        print("-" * 30)
        for k, v in summary.items():
            print(f"{k}: {v}")

        return results, summary


# ---------------------------------------------------------
if __name__ == "__main__":
    analyzer = PerformanceAnalyzer()
    analyzer.load()
    analyzer.analyze()
