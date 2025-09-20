# config.py - Full Updated with Multi-Strategy, Position Limits, and Risk Management

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ───────────────────────────────
# Deriv API Configuration
# ───────────────────────────────
APP_ID = os.getenv("APP_ID", "96293")
API_TOKEN = os.getenv("API_TOKEN", "")
SYMBOL = os.getenv("SYMBOL", "R_100")
GRANULARITY = int(os.getenv("GRANULARITY", 60))
HISTORY_COUNT = int(os.getenv("HISTORY_COUNT", 100))
# config.py
DERIV_WS_URL = os.getenv("DERIV_WS_URL", "wss://ws.binaryws.com/websockets/v3?app_id=" + APP_ID)


# ───────────────────────────────
# Trading Configuration
# ───────────────────────────────
TRADING_ENABLED = os.getenv("TRADING_ENABLED", "False").lower() == "true"
TRADE_EXECUTION = os.getenv("TRADE_EXECUTION", "demo")
INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", 10000))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", 0.02))

# ───────────────────────────────
# Multi-Strategy Configuration
# ───────────────────────────────
ACTIVE_STRATEGIES = os.getenv("ACTIVE_STRATEGIES", "scalper,snr_adx").split(",")
CAPITAL_ALLOCATION = {
    "scalper": float(os.getenv("SCALPER_CAPITAL_PERCENT", 80)) / 100,
    "snr_adx": float(os.getenv("SNR_ADX_CAPITAL_PERCENT", 20)) / 100
}

# ───────────────────────────────
# Server Configuration
# ───────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# ───────────────────────────────
# Risk Management
# ───────────────────────────────
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", 5))
STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", 1.5))
TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", 3.0))

# Time-Based Exit Rules
MAX_TRADE_DURATION = int(os.getenv("MAX_TRADE_DURATION", 1800))
MAX_TRADE_CANDLES = int(os.getenv("MAX_TRADE_CANDLES", 10))

# Emergency Stop Conditions
MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 2))
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", 150))
RISK_REDUCTION_MULTIPLIER = float(os.getenv("RISK_REDUCTION_MULTIPLIER", 0.5))
RECOVERY_MODE = os.getenv("RECOVERY_MODE", "False").lower() == "true"
MAX_RISK_PERCENT = float(os.getenv("MAX_RISK_PERCENT", 0.05))
MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", 40))  # Default reduced from 65

# Trade Costs
TRADE_COST_PERCENT = float(os.getenv("TRADE_COST_PERCENT", 0.07))

# ───────────────────────────────
# Position Limits
# ───────────────────────────────
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", 3))  # Global default
SCALPER_MAX_OPEN_POSITIONS = int(os.getenv("SCALPER_MAX_OPEN_POSITIONS", 2))
SNR_ADX_MAX_OPEN_POSITIONS = int(os.getenv("SNR_ADX_MAX_OPEN_POSITIONS", 3))

def get_max_open_positions(strategy_name):
    """Return max open positions for a given strategy"""
    if strategy_name == "scalper":
        return SCALPER_MAX_OPEN_POSITIONS
    elif strategy_name == "snr_adx":
        return SNR_ADX_MAX_OPEN_POSITIONS
    return MAX_OPEN_POSITIONS

# ───────────────────────────────
# Strategy-Specific Settings
# ───────────────────────────────

SCALPER_CONFIG = {
    "rsi_period": 7,
    "bollinger_period": 20,
    "bollinger_std": 2.0,
    "ema_fast": 9,
    "ema_slow": 21,
    "confidence_threshold": 55,
    "min_volatility": 0.2,
    "max_volatility": 1.0,
    "required_confirmations": 2,
    "signal_strength_threshold": 55,
    "max_consecutive_trades": 2,
    "daily_trade_limit": 5,
    "min_time_between_trades": 300,
    "min_adx": 10,
    "max_adx": 60,
    "bypass_adx_for_extremes": True,
    "profit_target": 1.5,
    "stop_loss": 1.0,
    "max_trade_duration": 900,
}

SNR_ADX_CONFIG = {
    "rsi_period": 14,
    "bollinger_period": 14,
    "bollinger_std": 1.8,
    "stochastic_period": 10,
    "ema_fast": 8,
    "ema_slow": 21,
    "confidence_threshold": 45,
    "min_volatility": 0.3,
    "max_volatility": 1.2,
    "required_confirmations": 3,
    "signal_strength_threshold": 60,
    "trend_filter_strength": 0.7,
    "volume_filter": True,
    "time_filter": True,
    "recovery_mode_multiplier": 0.5,
    "max_consecutive_trades": 3,
    "daily_trade_limit": 8,
    "min_time_between_trades": 180,
    "min_adx": 15,
    "max_adx": 70,
    "bypass_adx_for_extremes": True,
    # Additional advanced SNR+ADX parameters
    "snr_strength": 3,
    "breakout_confirmation": 2,
    "pullback_enabled": True,
    "volume_multiplier": 1.5,
    "max_snr_levels": 5,
    "snr_lookback": 50,
    "breakout_buffer": 0.001,
    "require_volume_confirmation": True,
    "require_candle_close": True,
    "use_fibonacci_extensions": True,
    "snr_tolerance": 0.001,
    "min_level_touches": 3,
    "level_strength_threshold": 4,
    "breakout_volume_multiplier": 1.5,
    "pullback_tolerance": 0.002,
    "max_pullback_candles": 5,
    "pullback_volume_ratio": 0.8,
    "min_risk_reward": 1.5,
    "trailing_stop_enabled": False,
    "trailing_stop_distance": 0.005,
    "cluster_based_detection": True,
    "cluster_tolerance": 0.002,
    "min_cluster_size": 3,
    "weight_recent_levels": True,
    "recent_level_weight": 1.5,
    "require_price_rejection": True,
    "rejection_threshold": 0.003,
    "min_bounce_strength": 2,
    "avoid_news_events": True,
    "trading_hours_only": False,
    "fibonacci_targets": [0.618, 1.0, 1.618],
}

STRATEGY_RISK_PARAMS = {
    "scalper": {
        "risk_per_trade": 0.01,
        "stop_loss_percent": 1.0,
        "take_profit_percent": 1.5,
        "max_daily_loss": 50,
    },
    "snr_adx": {
        "risk_per_trade": 0.015,
        "stop_loss_percent": 2.0,
        "take_profit_percent": 4.0,
        "max_daily_loss": 200,
    }
}

# ───────────────────────────────
# Helper Functions
# ───────────────────────────────
def get_strategy_balance(strategy_name):
    """Get initial balance for a strategy"""
    return INITIAL_BALANCE * CAPITAL_ALLOCATION.get(strategy_name, 0.5)

def get_strategy_risk(strategy_name):
    """Get risk per trade for a strategy"""
    return STRATEGY_RISK_PARAMS.get(strategy_name, {}).get('risk_per_trade', RISK_PER_TRADE)

def get_strategy_stop_loss(strategy_name):
    """Get stop loss percent for a strategy"""
    return STRATEGY_RISK_PARAMS.get(strategy_name, {}).get('stop_loss_percent', STOP_LOSS_PERCENT)

def get_strategy_take_profit(strategy_name):
    """Get take profit percent for a strategy"""
    return STRATEGY_RISK_PARAMS.get(strategy_name, {}).get('take_profit_percent', TAKE_PROFIT_PERCENT)

def get_strategy_daily_loss(strategy_name):
    """Get max daily loss for a strategy"""
    return STRATEGY_RISK_PARAMS.get(strategy_name, {}).get('max_daily_loss', MAX_DAILY_LOSS)

# ───────────────────────────────
# Configuration Summary
# ───────────────────────────────
print(f"✅ Configuration loaded. Trading enabled: {TRADING_ENABLED}")
print(f"   Active strategies: {', '.join(ACTIVE_STRATEGIES)}")
print(f"   Capital allocation: Scalper={CAPITAL_ALLOCATION['scalper']*100:.0f}%, SNR+ADX={CAPITAL_ALLOCATION['snr_adx']*100:.0f}%")
print(f"   Initial balances: Scalper=${get_strategy_balance('scalper'):.0f}, SNR+ADX=${get_strategy_balance('snr_adx'):.0f}")
print(f"   Risk levels: Scalper={get_strategy_risk('scalper')*100:.1f}%, SNR+ADX={get_strategy_risk('snr_adx')*100:.1f}%")
print(f"   Stop loss: Scalper={get_strategy_stop_loss('scalper')}%, SNR+ADX={get_strategy_stop_loss('snr_adx')}%")
print(f"   Take profit: Scalper={get_strategy_take_profit('scalper')}%, SNR+ADX={get_strategy_take_profit('snr_adx')}%")
print(f"   Max trade duration: {MAX_TRADE_DURATION//60} minutes")
print(f"   Trade cost: {TRADE_COST_PERCENT}%")
print(f"   Min confidence: {MIN_CONFIDENCE}%")
print(f"   Scalper confidence threshold: {SCALPER_CONFIG['confidence_threshold']}%")
print(f"   SNR+ADX confidence threshold: {SNR_ADX_CONFIG['confidence_threshold']}%")
print(f"   Max open positions: Global={MAX_OPEN_POSITIONS}, Scalper={SCALPER_MAX_OPEN_POSITIONS}, SNR+ADX={SNR_ADX_MAX_OPEN_POSITIONS}")
