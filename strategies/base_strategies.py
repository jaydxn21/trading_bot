# strategies/base_strategies.py
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    Unified base strategy.
    Compatible with:
    - TradingManager
    - Scalper / SuperScalper
    - Crash / Boom
    """

    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}

        self.capital = self.config.get("capital", 1000.0)
        self.min_confidence = self.config.get("min_confidence", 30)

        # HTF state (soft influence only)
        self.htf_context: Dict[str, Any] = {}
        self.htf_trend: Optional[str] = None
        self.htf_strength: float = 0.0

    # ─────────────────────────────────────────────
    # HTF HANDLING
    # ─────────────────────────────────────────────
    def ingest_htf_context(self, htf_context: Optional[Dict[str, Any]]):
        """Store HTF context safely."""
        if not htf_context:
            self.htf_context = {}
            self.htf_trend = "neutral"
            self.htf_strength = 0.0
            return

        self.htf_context = htf_context
        self.htf_trend = htf_context.get("trend", "neutral")
        self.htf_strength = float(htf_context.get("strength", 0))

    def adjust_confidence_with_htf(self, signal: str, confidence: int) -> int:
        """Soft HTF confidence adjustment."""
        if not self.htf_trend or self.htf_trend == "neutral":
            return confidence

        adj = 0

        # Strong trend alignment
        if self.htf_strength >= 40:
            if self.htf_trend == "bullish" and signal == "buy":
                adj = min(20, int(self.htf_strength / 2))
            elif self.htf_trend == "bearish" and signal == "sell":
                adj = min(20, int(self.htf_strength / 2))
            else:
                adj = -min(15, int(self.htf_strength / 3))

        # Moderate trend
        elif self.htf_strength >= 20:
            if self.htf_trend == signal:
                adj = 5

        final_conf = confidence + adj
        return int(max(10, min(95, final_conf)))

    # ─────────────────────────────────────────────
    # VALIDATION
    # ─────────────────────────────────────────────
    def validate_indicators(self, indicators: Dict[str, Any]) -> bool:
        required = ("rsi", "adx")
        for k in required:
            v = indicators.get(k)
            if v is None or np.isnan(v):
                return False
        return True

    # ─────────────────────────────────────────────
    # CONFIDENCE HELPERS
    # ─────────────────────────────────────────────
    def base_rsi_confidence(self, rsi: float, signal: str) -> int:
        if signal == "buy":
            if rsi <= 30:
                return int(60 + (30 - rsi))
            if rsi <= 45:
                return 40
        elif signal == "sell":
            if rsi >= 70:
                return int(60 + (rsi - 70))
            if rsi >= 55:
                return 40
        return 0

    # ─────────────────────────────────────────────
    # POSITION SIZING (SAFE FOR INDICES)
    # ─────────────────────────────────────────────
    def calculate_position_size(self, confidence: int) -> float:
        base_lot = self.config.get("base_lot", 0.01)
        max_lot = self.config.get("max_lot", 0.05)

        scale = max(0.2, confidence / 100)
        lot = base_lot + (max_lot - base_lot) * scale
        return round(lot, 2)

    # ─────────────────────────────────────────────
    # REQUIRED STRATEGY INTERFACE
    # ─────────────────────────────────────────────
    @abstractmethod
    def analyze_market(
        self,
        candles: List[Dict[str, Any]],
        current_price: float,
        indicators: Dict[str, Any],
        htf_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Must return:
        {
            "signal": "buy" | "sell" | "hold",
            "confidence": int
        }
        """
        pass

    # ─────────────────────────────────────────────
    # EXECUTION NORMALIZER
    # ─────────────────────────────────────────────
    def normalize_signal(
        self,
        signal: str,
        confidence: int,
        current_price: float
    ) -> Dict[str, Any]:
        if signal not in ("buy", "sell"):
            return {"signal": "hold", "confidence": 0}

        confidence = self.adjust_confidence_with_htf(signal, confidence)

        if confidence < self.min_confidence:
            return {"signal": "hold", "confidence": 0}

        return {
            "signal": signal,
            "confidence": int(confidence),
            "price": current_price,
            "strategy": self.name
        }

    # ─────────────────────────────────────────────
    # INFO
    # ─────────────────────────────────────────────
    def get_strategy_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "min_confidence": self.min_confidence,
            "htf_trend": self.htf_trend,
            "htf_strength": self.htf_strength,
            "config": self.config
        }
