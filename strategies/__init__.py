# -*- coding: utf-8 -*-
# strategies/__init__.py
"""
Dynamic strategy loader.
All files in this folder that contain a class inheriting from BaseStrategy
(and implementing `analyze_market`) will be auto-discovered and instantiated.
"""

import pkgutil
import importlib
import logging
from typing import Dict, Any, Type
from types import ModuleType

from .base_strategies import BaseStrategy

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# 1. USER-FACING MAPPING (aliases & canonical keys)
# --------------------------------------------------------------------------- #
#   class_name   →   canonical key used in the rest of the bot
STRATEGY_ALIASES: Dict[str, str] = {
    # Core strategies
    "ScalperStrategy": "scalper",
    "SCALPER_Strategy": "scalper",

    "Enhanced_SNR_ADX_Strategy": "snr_adx",
    "SNR_ADX_Strategy": "snr_adx",

    "Emergency_Overbought_Strategy": "emergency",
    "EMERGENCY_Strategy": "emergency",

    "Enhanced_SMA_Strategy": "enhanced_sma",
    "SMA_Strategy": "enhanced_sma",

    "SuperScalperStrategy": "super_scalper",

    # New / future strategies
    "VolMeanReversionStrategy": "vol_mean_reversion",
}

# --------------------------------------------------------------------------- #
# 2. GLOBAL CONTAINER
# --------------------------------------------------------------------------- #
STRATEGIES: Dict[str, BaseStrategy] = {}

# --------------------------------------------------------------------------- #
# 3. HELPER: instantiate a strategy class safely
# --------------------------------------------------------------------------- #
def _instantiate_strategy(strategy_cls: Type[BaseStrategy]) -> BaseStrategy:
    """Create an instance with an empty config dict. Fall back to no-arg init."""
    try:
        # Most strategies accept config={}
        return strategy_cls({})
    except TypeError:
        try:
            # Some may have no __init__ args at all
            return strategy_cls()
        except Exception as e:
            raise RuntimeError(f"Cannot instantiate {strategy_cls.__name__}") from e


# --------------------------------------------------------------------------- #
# 4. CORE LOADER
# --------------------------------------------------------------------------- #
def load_strategies() -> int:
    """Discover & instantiate every valid strategy in the package."""
    global STRATEGIES
    STRATEGIES.clear()
    loaded = 0

    logger.info("Loading trading strategies...")

    # Walk every module in the package
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if module_name.startswith("_") or module_name == "base_strategies":
            continue

        try:
            full_name = f"strategies.{module_name}"
            module: ModuleType = importlib.import_module(full_name)

            # Find all classes that inherit from BaseStrategy and have analyze_market
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseStrategy)
                    and attr is not BaseStrategy
                    and hasattr(attr, "analyze_market")
                ):
                    # Resolve canonical key
                    key = STRATEGY_ALIASES.get(attr.__name__, attr.__name__.replace("Strategy", "").lower())

                    if key in STRATEGIES:
                        logger.warning(f"Duplicate strategy key '{key}' – keeping the first one ({STRATEGIES[key].__class__.__name__})")
                        continue

                    try:
                        instance = _instantiate_strategy(attr)
                        STRATEGIES[key] = instance
                        loaded += 1
                        logger.info(f"Loaded: {key} ← {attr.__name__} ({module_name}.py)")
                    except Exception as e:
                        logger.error(f"Failed to instantiate {attr.__name__}: {e}")

        except Exception as e:
            logger.error(f"Failed to load module '{module_name}': {e}")

    # ------------------------------------------------------------------- #
    # 5. POST-LOAD VALIDATION
    # ------------------------------------------------------------------- #
    required = {"scalper", "snr_adx", "emergency", "enhanced_sma", "super_scalper"}
    missing = required - STRATEGIES.keys()
    if missing:
        logger.warning(f"Missing required strategies: {sorted(missing)}")
    else:
        logger.info("All required core strategies are loaded.")

    logger.info(f"Total strategies loaded: {loaded}")
    logger.info(f"Available keys: {sorted(STRATEGIES.keys())}")
    return loaded


# --------------------------------------------------------------------------- #
# 6. PUBLIC API
# --------------------------------------------------------------------------- #
def get_strategy(name: str) -> BaseStrategy | None:
    """Return a loaded strategy instance by its canonical key."""
    return STRATEGIES.get(name)


def list_strategies() -> Dict[str, Any]:
    """Return a dict with basic info for every loaded strategy."""
    info: Dict[str, Any] = {}
    for key, strat in STRATEGIES.items():
        try:
            info[key] = {
                "name": getattr(strat, "name", key),
                "min_confidence": getattr(strat, "min_confidence", "N/A"),
                "description": getattr(strat, "description", getattr(strat, "__doc__", "").strip()),
                "class": strat.__class__.__name__,
            }
        except Exception as e:
            info[key] = {"error": str(e)}
    return info


# --------------------------------------------------------------------------- #
# 7. AUTO-LOAD ON IMPORT
# --------------------------------------------------------------------------- #


__all__ = ["STRATEGIES", "get_strategy", "list_strategies"]