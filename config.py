# config.py - Centralized configuration with proper exports

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Deriv API Configuration
APP_ID = os.getenv("APP_ID", "96293")
API_TOKEN = os.getenv("API_TOKEN", "")
SYMBOL = os.getenv("SYMBOL", "R_100")
GRANULARITY = int(os.getenv("GRANULARITY", 60))
HISTORY_COUNT = int(os.getenv("HISTORY_COUNT", 100))

# Trading Configuration - TEMPORARY FOR TESTING
TRADING_ENABLED = os.getenv("TRADING_ENABLED", "False").lower() == "true"
TRADE_EXECUTION = os.getenv("TRADE_EXECUTION", "demo")
INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", 10000))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", 0.02))

# Strategy Configuration
ACTIVE_STRATEGY = os.getenv("ACTIVE_STRATEGY", "scalper")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Enhanced Risk Management
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", 5))
STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", 1.5))
TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", 3.0))

# Emergency Stop Conditions
MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 2))
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", 150))
RISK_REDUCTION_MULTIPLIER = float(os.getenv("RISK_REDUCTION_MULTIPLIER", 0.5))
RECOVERY_MODE = os.getenv("RECOVERY_MODE", "False").lower() == "true"
MAX_RISK_PERCENT = float(os.getenv("MAX_RISK_PERCENT", 0.05))
MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", 65))  # LOWERED FOR TESTING

# Strategy-specific settings
SCALPER_CONFIG = {
    "rsi_period": 7,
    "bollinger_period": 10,
    "stochastic_period": 14,
    "confidence_threshold": 65,  # LOWERED FOR TESTING
    "min_volatility": 0.2,
    "required_confirmations": 2
}

# Export all config variables for import
__all__ = [
    'APP_ID', 'API_TOKEN', 'SYMBOL', 'GRANULARITY', 'HISTORY_COUNT',
    'TRADING_ENABLED', 'TRADE_EXECUTION', 'INITIAL_BALANCE', 'RISK_PER_TRADE',
    'ACTIVE_STRATEGY', 'HOST', 'PORT', 'DEBUG', 'MAX_TRADES_PER_DAY',
    'STOP_LOSS_PERCENT', 'TAKE_PROFIT_PERCENT', 'MAX_CONSECUTIVE_LOSSES',
    'MAX_DAILY_LOSS', 'RISK_REDUCTION_MULTIPLIER', 'RECOVERY_MODE',
    'MAX_RISK_PERCENT', 'MIN_CONFIDENCE', 'SCALPER_CONFIG'
]

print(f"✅ Configuration loaded. Trading enabled: {TRADING_ENABLED}")
print(f"   Min confidence: {MIN_CONFIDENCE}%")