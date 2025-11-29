# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-# config.py - UPDATED with Super Scalper configuration
import os
from dotenv import load_dotenv
from datetime import datetime, time

# Load environment variables
load_dotenv()

# ───────────────────────────────
# Strategy Aliases
# ───────────────────────────────
STRATEGY_ALIASES = {
    'snr_adx': 'enhanced_snr_adx',
    'sma': 'enhanced_sma',
    'super_scalper': 'super_scalper'
}

def resolve_strategy_name(strat_name):
    """Resolve strategy aliases to actual strategy names."""
    return STRATEGY_ALIASES.get(strat_name.lower(), strat_name.lower())

# ───────────────────────────────
# Deriv API Configuration
# ───────────────────────────────
APP_ID = os.getenv("APP_ID", "1089")
API_TOKEN = os.getenv("API_TOKEN", "")
SYMBOL = os.getenv("SYMBOL", "R_100")
GRANULARITY = int(os.getenv("GRANULARITY", 60))
HISTORY_COUNT = int(os.getenv("HISTORY_COUNT", 100))
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
ACTIVE_STRATEGIES = os.getenv("ACTIVE_STRATEGIES", "scalper,snr_adx,emergency,super_scalper").split(",")
CAPITAL_ALLOCATION = {
    "scalper": float(os.getenv("SCALPER_CAPITAL_PERCENT", 30)) / 100,
    "snr_adx": float(os.getenv("SNR_ADX_CAPITAL_PERCENT", 30)) / 100,
    "emergency": float(os.getenv("EMERGENCY_CAPITAL_PERCENT", 10)) / 100,
    "enhanced_sma": float(os.getenv("SMA_CAPITAL_PERCENT", 10)) / 100,
    "super_scalper": float(os.getenv("SUPER_SCALPER_CAPITAL_PERCENT", 20)) / 100
}

# ───────────────────────────────
# Server Configuration
# ───────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# ───────────────────────────────
# Risk Management - UPDATED FOR R_100
# ───────────────────────────────
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", 20))

# UPDATED: Tighter stops for R_100 (typically moves 0.1-0.5% per tick)
STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", 0.5))    # Reduced from 1.5% to 0.5%
TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", 1.0)) # Reduced from 3.0% to 1.0%

# Time-Based Exit Rules
MAX_TRADE_DURATION = int(os.getenv("MAX_TRADE_DURATION", 480))  # 8 minutes for R_100
MAX_TRADE_CANDLES = int(os.getenv("MAX_TRADE_CANDLES", 8))

# Emergency Stop Conditions
MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 3))
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", 100))  # Reduced for tighter stops
RISK_REDUCTION_MULTIPLIER = float(os.getenv("RISK_REDUCTION_MULTIPLIER", 0.5))
RECOVERY_MODE = os.getenv("RECOVERY_MODE", "False").lower() == "true"
MAX_RISK_PERCENT = float(os.getenv("MAX_RISK_PERCENT", 0.03))  # Reduced max risk
MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", 25))  # Increased minimum confidence

# Trade Costs
TRADE_COST_PERCENT = float(os.getenv("TRADE_COST_PERCENT", 0.07))

# ───────────────────────────────
# Position Limits
# ───────────────────────────────
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", 5))  # Increased for burst trading
SCALPER_MAX_OPEN_POSITIONS = int(os.getenv("SCALPER_MAX_OPEN_POSITIONS", 1))
SNR_ADX_MAX_OPEN_POSITIONS = int(os.getenv("SNR_ADX_MAX_OPEN_POSITIONS", 2))
EMERGENCY_MAX_OPEN_POSITIONS = int(os.getenv("EMERGENCY_MAX_OPEN_POSITIONS", 1))
ENHANCED_SMA_MAX_OPEN_POSITIONS = int(os.getenv("ENHANCED_SMA_MAX_OPEN_POSITIONS", 1))
SUPER_SCALPER_MAX_OPEN_POSITIONS = int(os.getenv("SUPER_SCALPER_MAX_OPEN_POSITIONS", 5))  # For burst trades

def get_max_open_positions(strategy_name):
    """Return max open positions for a given strategy"""
    resolved_name = resolve_strategy_name(strategy_name)
    
    if resolved_name == "scalper":
        return SCALPER_MAX_OPEN_POSITIONS
    elif resolved_name == "enhanced_snr_adx":
        return SNR_ADX_MAX_OPEN_POSITIONS
    elif resolved_name == "emergency":
        return EMERGENCY_MAX_OPEN_POSITIONS
    elif resolved_name == "enhanced_sma":
        return ENHANCED_SMA_MAX_OPEN_POSITIONS
    elif resolved_name == "super_scalper":
        return SUPER_SCALPER_MAX_OPEN_POSITIONS
    return MAX_OPEN_POSITIONS

# ───────────────────────────────
# V100-Specific Optimizations - UPDATED FOR R_100
# ───────────────────────────────
V100_OPTIMIZED = {
    "min_confidence": 55,  # Increased for better quality signals
    "required_confirmations": 2,
    "volume_filter": True,
    "timeframe_alignment": ["1m", "5m"],  # Shorter timeframes for R_100
    "market_regime_weights": {
        "strong_trend_bullish": 0.8,
        "strong_trend_bearish": 0.8,
        "strong_trend_neutral": 0.7,
        "ranging": 0.3,  # Reduced weight for ranging markets
        "high_volatility": 0.6,
        "very_weak_trend": 0.2,  # Reduced weight for weak trends
        "transitioning": 0.5,
        "extreme_overbought": 0.8,  # Increased weight for extremes
        "extreme_oversold": 0.8
    },
    "optimal_hours": [
        {"start": time(9, 30), "end": time(11, 30)},
        {"start": time(14, 0), "end": time(16, 0)}
    ],
    "min_adx": 15,  # Increased for clearer trends
    "min_volume_ratio": 0.8,  # Reduced for R_100
    "rsi_filter_range": (25, 75)  # Tighter RSI range
}

def is_v100_optimal_time(current_time=None):
    """Check if current time is optimal for V100 signals"""
    if current_time is None:
        current_time = datetime.now().time()
    
    for period in V100_OPTIMIZED["optimal_hours"]:
        if period["start"] <= current_time <= period["end"]:
            return True
    return False

# ───────────────────────────────
# Strategy-Specific Settings - UPDATED FOR R_100
# ───────────────────────────────

SCALPER_CONFIG = {
    "rsi_period": 7,
    "bollinger_period": 20,
    "bollinger_std": 2.0,
    "ema_fast": 5,    # Faster EMA for R_100
    "ema_slow": 12,   # Adjusted slow EMA
    "confidence_threshold": 60,  # Increased confidence
    "min_volatility": 0.1,      # Lower volatility threshold for R_100
    "max_volatility": 0.8,      # Lower max volatility
    "required_confirmations": 2,
    "signal_strength_threshold": 70,  # Higher threshold
    "max_consecutive_trades": 2,
    "daily_trade_limit": 8,     # Increased for R_100
    "min_time_between_trades": 120,  # Shorter cooldown
    "min_adx": 12,    # Lower ADX for scalping
    "max_adx": 50,
    "bypass_adx_for_extremes": True,
    "profit_target": 0.6,   # Tighter for R_100
    "stop_loss": 0.3,       # Tighter for R_100
    "max_trade_duration": 300,  # 5 minutes for scalping
}

ENHANCED_SNR_ADX_CONFIG = {
    "rsi_period": 14,
    "bollinger_period": 14,
    "bollinger_std": 1.8,
    "stochastic_period": 10,
    "ema_fast": 8,
    "ema_slow": 21,
    "confidence_threshold": 65,  # Increased confidence
    "min_volatility": 0.2,      # Adjusted for R_100
    "max_volatility": 1.0,      # Adjusted for R_100
    "required_confirmations": 2, # Reduced confirmations
    "signal_strength_threshold": 70, # Higher threshold
    "trend_filter_strength": 0.7,
    "volume_filter": True,
    "time_filter": True,
    "recovery_mode_multiplier": 0.5,
    "max_consecutive_trades": 2, # Reduced consecutive trades
    "daily_trade_limit": 6,     # Reasonable daily limit
    "min_time_between_trades": 180,
    "min_adx": 15,    # Require clearer trends
    "max_adx": 60,
    "bypass_adx_for_extremes": True,
    "snr_strength": 3,
    "breakout_confirmation": 2,
    "pullback_enabled": True,
    "volume_multiplier": 1.5,
    "max_snr_levels": 5,
    "snr_lookback": 50,
    "breakout_buffer": 0.0005,  # Tighter buffer for R_100
    "require_volume_confirmation": True,
    "require_candle_close": True,
    "use_fibonacci_extensions": True,
    "snr_tolerance": 0.003,     # Tighter tolerance for R_100
    "min_level_touches": 3,
    "level_strength_threshold": 4,
    "breakout_volume_multiplier": 1.5,
    "pullback_tolerance": 0.001, # Tighter pullback tolerance
    "max_pullback_candles": 3,   # Fewer pullback candles
    "pullback_volume_ratio": 0.8,
    "min_risk_reward": 2.0,     # Better risk-reward
    "trailing_stop_enabled": True,  # Enable trailing stops
    "trailing_stop_distance": 0.002, # Tighter trailing stop
    "cluster_based_detection": True,
    "cluster_tolerance": 0.001,  # Tighter cluster tolerance
    "min_cluster_size": 3,
    "weight_recent_levels": True,
    "recent_level_weight": 1.5,
    "require_price_rejection": True,
    "rejection_threshold": 0.002, # Tighter rejection threshold
    "min_bounce_strength": 2,
    "avoid_news_events": True,
    "trading_hours_only": False,
    "fibonacci_targets": [0.382, 0.618, 1.0],  # Adjusted Fibonacci levels
}

EMERGENCY_CONFIG = {
    "min_confidence": 25,       # Increased minimum confidence
    "rsi_overbought_threshold": 85,  # Tighter overbought
    "rsi_oversold_threshold": 15,    # Tighter oversold
    "max_trade_duration": 600,  # 10 minutes for emergency trades
    "risk_multiplier": 0.5,     # Lower risk for emergency trades
}

ENHANCED_SMA_CONFIG = {
    "min_confidence": 20,
    "fast_period": 9,
    "slow_period": 21,
    "max_trade_duration": 600,  # 10 minutes
}

# ───────────────────────────────
# SUPER SCALPER CONFIGURATION
# ───────────────────────────────
SUPER_SCALPER_CONFIG = {
    "enabled": True,
    "burst_interval_minutes": 10,
    "trades_per_burst": 5,
    "target_profit_percent": 20,
    "max_stake_per_trade": 3.0,
    "max_daily_bursts": 12,  # Max 12 bursts per day (2 hours total)
    "min_confidence": 70,
    "cooldown_after_loss": 30,  # minutes cooldown after losing burst
    
    # Trading parameters
    "rsi_period": 5,
    "ema_fast": 3,
    "ema_slow": 8,
    "min_volatility": 0.001,
    "max_volatility": 0.005,
    "max_trade_duration": 180,  # 3 minutes for ultra-fast scalping
    "stop_loss_percent": 0.2,   # Very tight stop loss
    "take_profit_percent": 20,  # 20% target profit
    "daily_trade_limit": 60,    # 12 bursts * 5 trades
    "min_time_between_bursts": 600,  # 10 minutes
}

# ───────────────────────────────
# Strategy Risk Parameters - UPDATED FOR R_100
# ───────────────────────────────
STRATEGY_RISK_PARAMS = {
    "scalper": {
        "risk_per_trade": 0.01,      # 1% risk for scalper
        "stop_loss_percent": 0.3,    # 0.3% stop loss
        "take_profit_percent": 0.6,  # 0.6% take profit
        "max_daily_loss": 30,        # $30 max daily loss
    },
    "snr_adx": {
        "risk_per_trade": 0.015,     # 1.5% risk
        "stop_loss_percent": 0.5,    # 0.5% stop loss
        "take_profit_percent": 1.0,  # 1.0% take profit
        "max_daily_loss": 50,        # $50 max daily loss
    },
    "emergency": {
        "risk_per_trade": 0.008,     # 0.8% risk for emergency
        "stop_loss_percent": 0.4,    # 0.4% stop loss
        "take_profit_percent": 0.8,  # 0.8% take profit
        "max_daily_loss": 25,        # $25 max daily loss
    },
    "enhanced_sma": {
        "risk_per_trade": 0.01,      # 1% risk
        "stop_loss_percent": 0.4,    # 0.4% stop loss
        "take_profit_percent": 0.8,  # 0.8% take profit
        "max_daily_loss": 30,        # $30 max daily loss
    },
    "super_scalper": {
        "risk_per_trade": 0.005,     # 0.5% risk per trade in burst
        "stop_loss_percent": 0.2,    # 0.2% stop loss
        "take_profit_percent": 20,   # 20% profit target
        "max_daily_loss": 50,        # $50 max daily loss
        "max_burst_loss": 10,        # $10 max loss per burst
    }
}

# ───────────────────────────────
# Helper Functions
# ───────────────────────────────
def get_strategy_balance(strategy_name):
    """Get initial balance for a strategy"""
    resolved_name = resolve_strategy_name(strategy_name)
    return INITIAL_BALANCE * CAPITAL_ALLOCATION.get(resolved_name, 0.5)

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
# Strategy Configuration Mapping
# ───────────────────────────────

STRATEGY_CONFIG = {
    "scalper": {
        "enabled": "scalper" in ACTIVE_STRATEGIES,
        "capital": get_strategy_balance("scalper"),
        "risk_per_trade": get_strategy_risk("scalper"),
        "stop_loss": get_strategy_stop_loss("scalper"),
        "take_profit": get_strategy_take_profit("scalper"),
        "max_open_trades": get_max_open_positions("scalper"),
        "min_confidence": SCALPER_CONFIG["confidence_threshold"],
        "fast_ema": SCALPER_CONFIG["ema_fast"],
        "slow_ema": SCALPER_CONFIG["ema_slow"], 
        "rsi_period": SCALPER_CONFIG["rsi_period"],
        "min_adx": SCALPER_CONFIG["min_adx"],
        "max_adx": SCALPER_CONFIG["max_adx"],
        **SCALPER_CONFIG
    },
    "snr_adx": {
        "enabled": "snr_adx" in ACTIVE_STRATEGIES,
        "capital": get_strategy_balance("snr_adx"),
        "risk_per_trade": get_strategy_risk("snr_adx"),
        "stop_loss": get_strategy_stop_loss("snr_adx"),
        "take_profit": get_strategy_take_profit("snr_adx"),
        "max_open_trades": get_max_open_positions("snr_adx"),
        "min_confidence": ENHANCED_SNR_ADX_CONFIG["confidence_threshold"],
        "min_adx": ENHANCED_SNR_ADX_CONFIG["min_adx"],
        "max_adx": ENHANCED_SNR_ADX_CONFIG["max_adx"],
        "sr_tolerance": ENHANCED_SNR_ADX_CONFIG["snr_tolerance"],
        "rsi_period": ENHANCED_SNR_ADX_CONFIG["rsi_period"],
        **ENHANCED_SNR_ADX_CONFIG
    },
    "emergency": {
        "enabled": "emergency" in ACTIVE_STRATEGIES,
        "capital": get_strategy_balance("emergency"),
        "risk_per_trade": get_strategy_risk("emergency"),
        "stop_loss": get_strategy_stop_loss("emergency"),
        "take_profit": get_strategy_take_profit("emergency"),
        "max_open_trades": get_max_open_positions("emergency"),
        "min_confidence": EMERGENCY_CONFIG["min_confidence"],
        "rsi_overbought_threshold": EMERGENCY_CONFIG["rsi_overbought_threshold"],
        "rsi_oversold_threshold": EMERGENCY_CONFIG["rsi_oversold_threshold"],
        **EMERGENCY_CONFIG
    },
    "enhanced_sma": {
        "enabled": "enhanced_sma" in ACTIVE_STRATEGIES,
        "capital": get_strategy_balance("enhanced_sma"),
        "risk_per_trade": get_strategy_risk("enhanced_sma"),
        "stop_loss": get_strategy_stop_loss("enhanced_sma"),
        "take_profit": get_strategy_take_profit("enhanced_sma"),
        "max_open_trades": get_max_open_positions("enhanced_sma"),
        "min_confidence": ENHANCED_SMA_CONFIG["min_confidence"],
        "fast_period": ENHANCED_SMA_CONFIG["fast_period"],
        "slow_period": ENHANCED_SMA_CONFIG["slow_period"],
        **ENHANCED_SMA_CONFIG
    },
    "super_scalper": {
        "enabled": "super_scalper" in ACTIVE_STRATEGIES,
        "capital": get_strategy_balance("super_scalper"),
        "risk_per_trade": get_strategy_risk("super_scalper"),
        "stop_loss": get_strategy_stop_loss("super_scalper"),
        "take_profit": get_strategy_take_profit("super_scalper"),
        "max_open_trades": get_max_open_positions("super_scalper"),
        "min_confidence": SUPER_SCALPER_CONFIG["min_confidence"],
        "burst_interval": SUPER_SCALPER_CONFIG["burst_interval_minutes"],
        "trades_per_burst": SUPER_SCALPER_CONFIG["trades_per_burst"],
        "target_profit_percent": SUPER_SCALPER_CONFIG["target_profit_percent"],
        "max_daily_bursts": SUPER_SCALPER_CONFIG["max_daily_bursts"],
        **SUPER_SCALPER_CONFIG
    }
}

# ───────────────────────────────
# Configuration Summary
# ───────────────────────────────
print(f"✅ Configuration loaded. Trading enabled: {TRADING_ENABLED}")
print(f"   Active strategies: {', '.join(ACTIVE_STRATEGIES)}")
print(f"   Strategy aliases: {STRATEGY_ALIASES}")
print(f"   Capital allocation: Scalper={CAPITAL_ALLOCATION['scalper']*100:.0f}%, "
      f"SNR+ADX={CAPITAL_ALLOCATION['snr_adx']*100:.0f}%, "
      f"Emergency={CAPITAL_ALLOCATION['emergency']*100:.0f}%, "
      f"Super Scalper={CAPITAL_ALLOCATION['super_scalper']*100:.0f}%")
print(f"   Min confidence: {MIN_CONFIDENCE}%")
print(f"   Strategy confidence thresholds:")
for name in ACTIVE_STRATEGIES:
    conf = STRATEGY_CONFIG.get(name, {}).get('min_confidence', 'N/A')
    print(f"     {name}: {conf}%")
print(f"   Emergency RSI thresholds: Overbought>{EMERGENCY_CONFIG['rsi_overbought_threshold']}%, "
      f"Oversold<{EMERGENCY_CONFIG['rsi_oversold_threshold']}%")
print(f"   V100 TUNED Optimizations: ADX>{V100_OPTIMIZED['min_adx']}, Volume>{V100_OPTIMIZED['min_volume_ratio']:.1f}")
print(f"   R_100 Risk Parameters:")
print(f"     Global Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"     Global Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"     Max Trade Duration: {MAX_TRADE_DURATION}s ({MAX_TRADE_DURATION//60}min)")
print(f"   Super Scalper Settings:")
print(f"     Burst Interval: {SUPER_SCALPER_CONFIG['burst_interval_minutes']}min")
print(f"     Trades per Burst: {SUPER_SCALPER_CONFIG['trades_per_burst']}")
print(f"     Target Profit: {SUPER_SCALPER_CONFIG['target_profit_percent']}%")
print(f"     Max Daily Bursts: {SUPER_SCALPER_CONFIG['max_daily_bursts']}")
print(f"   Strategy-specific stops:")
for name in ACTIVE_STRATEGIES:
    sl = STRATEGY_RISK_PARAMS.get(name, {}).get('stop_loss_percent', 'N/A')
    tp = STRATEGY_RISK_PARAMS.get(name, {}).get('take_profit_percent', 'N/A')
    print(f"     {name}: SL={sl}%, TP={tp}%")
# FIXED SYMBOL CONFIGURATION FOR SUPER SCALPER
# Available Deriv symbols for different strategies
DERIV_SYMBOLS = {
    "forex": ["frxEURUSD", "frxGBPUSD", "frxUSDJPY"],
    "volatility": ["R_100", "R_50", "R_25"],
    "crypto": ["BTCUSD", "ETHUSD"],
    "indices": ["WLDAUD", "WLDUSD"]
}

# Strategy-specific symbol preferences
STRATEGY_SYMBOLS = {
    "scalper": "R_100",           # Good for scalping
    "snr_adx": "frxEURUSD",       # Good for trend strategies
    "emergency": "R_100",         # Good for emergency signals
    "enhanced_sma": "frxEURUSD",  # Good for moving average strategies
    "super_scalper": "R_100"      # Best for burst trading
}

def get_strategy_symbol(strategy_name):
    """Get optimal symbol for each strategy"""
    return STRATEGY_SYMBOLS.get(strategy_name, SYMBOL)

# Update the main symbol to R_100 for better volatility
SYMBOL = "R_100"
