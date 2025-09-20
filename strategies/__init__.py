# strategies/__init__.py
import pkgutil
import importlib
from pathlib import Path
from typing import Dict, Any

__all__ = []

# Default configs per strategy (add new strategies here if needed)
DEFAULT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "SNR_ADX": {"min_adx": 20, "max_adx": 60},
    "SMA": {"fast": 9, "slow": 21},
}

# Dynamically import all modules in this folder
for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    module = importlib.import_module(f"{__name__}.{module_name}")
    globals()[module_name] = module
    __all__.append(module_name)

# Initialize strategy instances dynamically
STRATEGIES = {}
for module_name in __all__:
    cls_name = "".join([part.capitalize() for part in module_name.split("_")]) + "_Strategy"
    strategy_cls = getattr(globals()[module_name], cls_name, None)
    if strategy_cls:
        config = DEFAULT_CONFIGS.get(cls_name.replace("_Strategy", ""), {})
        STRATEGIES[cls_name.replace("_Strategy", "")] = strategy_cls(config)
