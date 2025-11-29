# ai_core.py
import numpy as np
import joblib
import os
from datetime import datetime
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class MLTradePredictor:
    def __init__(self, model_path: str = "ml_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            try:
                data = joblib.load(self.model_path)
                self.model = data.get("model")
                self.scaler = data.get("scaler")
                logger.info("ML model loaded")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self._create_dummy_model()
        else:
            logger.warning("No ML model found. Using dummy predictor.")
            self._create_dummy_model()

    def _create_dummy_model(self):
        from sklearn.linear_model import LogisticRegression
        self.model = LogisticRegression()
        self.scaler = None

    def extract_features(self, candles: List[Dict], indicators: Dict, price: float, strategy: str) -> np.ndarray:
        if len(candles) < 20:
            return np.zeros(10)

        closes = np.array([c['close'] for c in candles[-20:]])
        highs = np.array([c['high'] for c in candles[-20:]])
        lows = np.array([c['low'] for c in candles[-20:]])

        rsi = indicators.get('rsi', 50)
        adx = indicators.get('adx', 20)
        volatility = indicators.get('volatility', 0.002)
        sma_fast = indicators.get('sma_fast', price)
        sma_slow = indicators.get('sma_slow', price)

        features = [
            rsi / 100.0,
            adx / 100.0,
            volatility * 1000,
            (price - sma_fast) / price if price > 0 else 0,
            (price - sma_slow) / price if price > 0 else 0,
            np.std(closes) / np.mean(closes) if np.mean(closes) > 0 else 0,
            (highs[-1] - lows[-1]) / price if price > 0 else 0,
            1.0 if strategy == "scalper" else 0.0,
            1.0 if strategy == "snr_adx" else 0.0,
            1.0 if strategy == "super_scalper" else 0.0,
        ]
        return np.array(features).reshape(1, -1)

    def predict_success_probability(self, candles: List[Dict], indicators: Dict, price: float, strategy: str) -> float:
        if not self.model:
            return 0.65  # default confidence

        try:
            X = self.extract_features(candles, indicators, price, strategy)
            if self.scaler:
                X = self.scaler.transform(X)
            prob = self.model.predict_proba(X)[0][1]
            return float(prob)
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return 0.5

    def learn_from_trade(self, trade_data: Dict, was_executed: bool = True):
        # In real use: collect data for retraining
        pass


class AIStrategyOptimizer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.enabled = bool(api_key)
        if self.enabled:
            try:
                import openai
                openai.api_key = api_key
                logger.info("OpenAI API ready for strategy optimization")
            except ImportError:
                logger.warning("openai package not installed. AI optimizer disabled.")
                self.enabled = False
        else:
            logger.info("No OpenAI key – AI optimizer disabled")

    def optimize_strategy(self, strategy_name: str, performance: Dict) -> Dict[str, Any]:
        if not self.enabled:
            return {"optimized": False, "reason": "AI disabled"}

        prompt = f"""
You are a trading systems expert. Optimize the '{strategy_name}' strategy.

Current performance:
- Win rate: {performance.get('win_rate', 0):.1f}%
- Total trades: {performance.get('total_trades', 0)}
- Net PnL: ${performance.get('total_pnl', 0):.2f}
- Consecutive losses: {performance.get('consecutive_losses', 0)}

Suggest parameter changes to improve win rate and reduce drawdown.
Return JSON with: min_confidence, stop_loss_percent, take_profit_percent, and reasoning.
"""

        try:
            import openai
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            result = response.choices[0].message.content.strip()
            import json
            try:
                parsed = json.loads(result)
                return {"optimized": True, "suggestions": parsed}
            except:
                return {"optimized": False, "raw": result}
        except Exception as e:
            logger.error(f"AI optimization failed: {e}")
            return {"optimized": False, "error": str(e)}