# config_loader.py - Enhanced version
import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manage trading configuration with file-based overrides."""
    
    def __init__(self, config_file: str = "trading_config.json"):
        self.config_file = config_file
        self.default_config = self._get_default_config()
        self.user_config = {}
        self.last_modified = None
        self.load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration structure."""
        return {
            "trading": {
                "enabled": True,
                "initial_balance": 10000,
                "risk_per_trade": 0.02,
                "max_daily_loss": 150,
                "min_confidence": 25
            },
            "strategies": {
                "emergency": {
                    "enabled": True,
                    "min_confidence": 10,
                    "rsi_overbought": 85,
                    "rsi_oversold": 15,
                    "risk_multiplier": 0.7
                },
                "snr_adx": {
                    "enabled": True,
                    "min_confidence": 20,
                    "sr_tolerance": 0.005,
                    "min_adx": 10,
                    "max_adx": 70
                },
                "sma": {
                    "enabled": True,
                    "min_confidence": 15,
                    "fast_period": 9,
                    "slow_period": 21
                }
            },
            "indicators": {
                "rsi_period": 14,
                "adx_period": 14,
                "bb_period": 20,
                "bb_std": 2.0
            },
            "risk_management": {
                "max_open_positions": 3,
                "max_consecutive_losses": 3,
                "cooldown_minutes": 2,
                "emergency_cooldown": 1
            }
        }
    
    def load_config(self) -> bool:
        """Load configuration from file with hot-reload capability."""
        if not os.path.exists(self.config_file):
            logger.warning(f"⚠️ Config file not found: {self.config_file}. Using defaults.")
            self.user_config = {}
            return False
        
        try:
            # Check if file was modified
            current_modified = os.path.getmtime(self.config_file)
            if self.last_modified == current_modified:
                return True  # No changes
            
            with open(self.config_file, "r") as f:
                self.user_config = json.load(f)
            
            self.last_modified = current_modified
            logger.info(f"✅ Config loaded from {self.config_file}")
            self._validate_config()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            self.user_config = {}
            return False
    
    def _validate_config(self):
        """Validate configuration values."""
        if not isinstance(self.user_config, dict):
            raise ValueError("Config must be a dictionary")
        
        # Validate trading parameters
        trading = self.get("trading", {})
        if trading.get("risk_per_trade", 0) > 0.1:
            logger.warning("⚠️ High risk per trade detected (>10%)")
        
        # Validate strategy configurations
        strategies = self.get("strategies", {})
        for name, config in strategies.items():
            if config.get("enabled", False):
                min_conf = config.get("min_confidence", 0)
                if min_conf < 5 or min_conf > 95:
                    logger.warning(f"⚠️ Strategy {name} has unusual min_confidence: {min_conf}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation support."""
        try:
            # Support dot notation: "strategies.emergency.min_confidence"
            keys = key.split('.')
            value = self.user_config
            
            for k in keys:
                value = value.get(k, {})
            
            if value == {}:  # Key not found in user config
                value = self.default_config
                for k in keys:
                    value = value.get(k, default)
            
            return value if value != {} else default
            
        except (AttributeError, KeyError):
            return default
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for a specific strategy."""
        strategy_config = self.get(f"strategies.{strategy_name}", {})
        
        # Merge with default strategy config
        default_strategy = self.default_config["strategies"].get(strategy_name, {})
        return {**default_strategy, **strategy_config}
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update configuration and save to file."""
        try:
            # Deep merge updates
            self._deep_merge(self.user_config, updates)
            
            # Save to file
            with open(self.config_file, "w") as f:
                json.dump(self.user_config, f, indent=2)
            
            logger.info(f"✅ Config updated and saved to {self.config_file}")
            self.last_modified = os.path.getmtime(self.config_file)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update config: {e}")
            return False
    
    def _deep_merge(self, target: Dict, source: Dict):
        """Deep merge two dictionaries."""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def get_active_strategies(self) -> list:
        """Get list of enabled strategies."""
        strategies = self.get("strategies", {})
        return [name for name, config in strategies.items() if config.get("enabled", False)]
    
    def get_trading_status(self) -> Dict[str, Any]:
        """Get current trading configuration status."""
        return {
            "trading_enabled": self.get("trading.enabled", False),
            "initial_balance": self.get("trading.initial_balance", 10000),
            "risk_per_trade": self.get("trading.risk_per_trade", 0.02),
            "active_strategies": self.get_active_strategies(),
            "config_file": self.config_file,
            "last_modified": datetime.fromtimestamp(self.last_modified).isoformat() if self.last_modified else "Never",
            "using_defaults": not self.user_config
        }

# Global config instance
config_manager = ConfigManager()

# Backward compatibility function
def load_config(file_path: str = "trading_config.json") -> dict:
    """Legacy function for backward compatibility."""
    global config_manager
    config_manager = ConfigManager(file_path)
    return config_manager.user_config