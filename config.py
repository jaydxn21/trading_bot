# config.py — QUANTUMTRADER PRO v7.2 — OPTIMIZED FOR TP HITS
import os
from dotenv import load_dotenv
from typing import Dict, Any
from datetime import datetime

load_dotenv()

# ── API & SYMBOL ─────────────────────────────────────────────────────────────
APP_ID = os.getenv("APP_ID", "111074")
API_TOKEN = os.getenv("API_TOKEN", "").strip()

if not API_TOKEN:
    raise ValueError("API_TOKEN IS MISSING! ADD IT TO .env FILE.")

SYMBOL = os.getenv("SYMBOL", "R_100")
GRANULARITY = int(os.getenv("GRANULARITY", "60"))
HISTORY_COUNT = int(os.getenv("HISTORY_COUNT", "100"))

# ── TRADING MODE ────────────────────────────────────────────────────────────
TRADING_ENABLED = os.getenv("TRADING_ENABLED", "False").lower() == "true"
TRADE_EXECUTION = os.getenv("TRADE_EXECUTION", "demo").lower()
IS_DEMO = TRADE_EXECUTION != "real"
INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "1000"))

print(f"🔧 SCALPER MODE: {'DEMO' if IS_DEMO else 'REAL'} | TRADING={'ENABLED' if TRADING_ENABLED else 'DISABLED'}")

# ── ACTIVE STRATEGIES ───────────────────────────────────────────────────────
_active_raw = os.getenv("ACTIVE_STRATEGIES", "scalper,emergency")
ACTIVE_STRATEGIES = [s.strip() for s in _active_raw.split(",") if s.strip()]

# ── SCALPER-FOCUSED CAPITAL ALLOCATION ──────────────────────────────────────
CAPITAL_ALLOCATION = {
    "scalper":        float(os.getenv("SCALPER_CAPITAL_PERCENT", "90")) / 100,   # MAX to scalper
    "emergency":      float(os.getenv("EMERGENCY_CAPITAL_PERCENT", "10")) / 100, # Minimal safety
    "snr_adx":        float(os.getenv("SNR_ADX_CAPITAL_PERCENT", "0")) / 100,
    "enhanced_sma":   float(os.getenv("SMA_CAPITAL_PERCENT", "0")) / 100,
    "super_scalper":  float(os.getenv("SUPER_SCALPER_CAPITAL_PERCENT", "0")) / 100,
    "vol_mean_reversion": float(os.getenv("VOL_MEAN_REVERSION_CAPITAL_PERCENT", "0")) / 100,
}

# ── HIGH-FREQUENCY RISK SETTINGS ────────────────────────────────────────────
RISK_PER_TRADE          = float(os.getenv("RISK_PER_TRADE", "0.01"))
MAX_TRADE_AMOUNT        = float(os.getenv("MAX_TRADE_AMOUNT", "2"))
MAX_TRADES_PER_DAY      = int(os.getenv("MAX_TRADES_PER_DAY", "50"))        # HIGH FREQUENCY
MAX_OPEN_POSITIONS      = int(os.getenv("MAX_OPEN_POSITIONS", "5"))         # Multiple positions
MAX_CONSECUTIVE_LOSSES  = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "5"))     # Higher for scalping
MAX_DAILY_LOSS          = float(os.getenv("DAILY_LOSS_LIMIT", "100"))       # Higher limit
STOP_LOSS_PERCENT       = float(os.getenv("STOP_LOSS_PERCENT", "0.5"))
TAKE_PROFIT_PERCENT     = float(os.getenv("TAKE_PROFIT_PERCENT", "1.0"))
MAX_TRADE_DURATION      = int(os.getenv("MAX_TRADE_DURATION", "15"))        # INCREASED: 10→15 minutes
MAX_TRADE_CANDLES       = int(os.getenv("MAX_TRADE_CANDLES", "3"))          # Very short
MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", "50"))                     # INCREASED: 30→50% for better signals
TRADE_COST_PERCENT      = float(os.getenv("TRADE_COST_PERCENT", "0.07"))

# ── SCALPER-SPECIFIC RISK PARAMS ────────────────────────────────────────────
STRATEGY_RISK_PARAMS = {
    "scalper": {
        "risk_per_trade":      float(os.getenv("SCALPER_RISK_PER_TRADE", "0.02")),  # Higher risk
        "stop_loss_percent":   float(os.getenv("SCALPER_STOP_LOSS_PERCENT", "0.3")), # WIDER: 0.2→0.3%
        "take_profit_percent": float(os.getenv("SCALPER_TAKE_PROFIT_PERCENT", "0.3")), # CLOSER: 0.4→0.3% (1:1 R/R)
        "max_daily_loss":      float(os.getenv("SCALPER_MAX_DAILY_LOSS", "100")),   # Higher limit
        "max_open_trades":     int(os.getenv("SCALPER_MAX_OPEN_POSITIONS", "3")),   # Multiple positions
    },
    "snr_adx": {
        "risk_per_trade":      0.0,    # Disabled
        "stop_loss_percent":   0.5,
        "take_profit_percent": 1.0,
        "max_daily_loss":      0,
        "max_open_trades":     0,
    },
    "emergency": { 
        "risk_per_trade":      float(os.getenv("EMERGENCY_RISK_PER_TRADE", "0.005")),
        "stop_loss_percent":   float(os.getenv("EMERGENCY_STOP_LOSS_PERCENT", "0.3")),
        "take_profit_percent": float(os.getenv("EMERGENCY_TAKE_PROFIT_PERCENT", "0.6")),
        "max_daily_loss":      float(os.getenv("EMERGENCY_MAX_DAILY_LOSS", "20")),
        "max_open_trades":     int(os.getenv("EMERGENCY_MAX_OPEN_POSITIONS", "1")),
    },
    "enhanced_sma": { "risk_per_trade": 0.0, "stop_loss_percent": 0.4, "take_profit_percent": 0.8, "max_daily_loss": 0, "max_open_trades": 0 },
    "super_scalper": { "risk_per_trade": 0.0, "stop_loss_percent": 0.2, "take_profit_percent": 20.0, "max_daily_loss": 0, "max_burst_loss": 0, "max_open_trades": 0 },
    "vol_mean_reversion": { "risk_per_trade": 0.0, "stop_loss_percent": 0.4, "take_profit_percent": 0.8, "max_daily_loss": 0, "max_open_trades": 0 },
}

# ── SCALPER-OPTIMIZED INDICATOR SETTINGS ────────────────────────────────────
SCALPER_CONFIG = { 
    "rsi_period": 5,                  # Faster RSI for scalping
    "bollinger_period": 10,           # Shorter Bollinger for scalping
    "bollinger_std": 1.5,             # Tighter bands
    "ema_fast": 3,                    # Very fast EMA
    "ema_slow": 8,                    # Fast slow EMA
    "min_confidence": 60,             # INCREASED: 40→60% for higher quality signals
    "min_adx": 15,                    # INCREASED: 10→15 for stronger trends
    "max_adx": 80,                    # Higher max ADX
    "max_confidence": 95,
    "trade_duration": 8,              # INCREASED: 5→8 minutes for more TP hits
    "cooldown_seconds": 10,           # Short cooldown between trades
}
ENHANCED_SNR_ADX_CONFIG = { "enabled": False }
EMERGENCY_CONFIG = { 
    "min_confidence": 50, 
    "rsi_overbought_threshold": 90,   # More sensitive
    "rsi_oversold_threshold": 10,     # More sensitive
    "risk_multiplier": 0.3, 
    "max_trade_duration": 600, 
    "max_confidence": 95 
}
ENHANCED_SMA_CONFIG = { "enabled": False }
SUPER_SCALPER_CONFIG = { "enabled": False }
VOL_MEAN_REVERSION_CONFIG = { "enabled": False }

# ── BUILD STRATEGY CONFIG ───────────────────────────────────────────────────
def build_strategy_config():
    cfg = {}
    for key in ACTIVE_STRATEGIES:
        risk = STRATEGY_RISK_PARAMS.get(key, {})
        base = {
            "enabled": True,
            "capital": INITIAL_BALANCE * CAPITAL_ALLOCATION.get(key, 0.0),
            "risk_per_trade": risk.get("risk_per_trade", RISK_PER_TRADE),
            "stop_loss_percent": risk.get("stop_loss_percent", STOP_LOSS_PERCENT),
            "take_profit_percent": risk.get("take_profit_percent", TAKE_PROFIT_PERCENT),
            "max_open_trades": risk.get("max_open_trades", MAX_OPEN_POSITIONS),
            "max_daily_loss": risk.get("max_daily_loss", MAX_DAILY_LOSS),
            "max_trade_amount": MAX_TRADE_AMOUNT,
            "max_confidence": 95,
        }
        
        if key == "scalper": 
            base.update(SCALPER_CONFIG)
            # Calculate actual R/R ratio
            rr_ratio = risk.get("take_profit_percent", 0.3) / risk.get("stop_loss_percent", 0.3)
            print(f"✅ SCALPER ENABLED: {CAPITAL_ALLOCATION.get(key, 0)*100}% capital | Risk: {risk.get('risk_per_trade', 0)*100}%")
            print(f"   R/R Ratio: {rr_ratio:.1f}:1 | TP: {risk.get('take_profit_percent', 0)}% | SL: {risk.get('stop_loss_percent', 0)}%")
        elif key == "emergency": 
            base.update(EMERGENCY_CONFIG)
            print(f"🛡️  EMERGENCY ENABLED: {CAPITAL_ALLOCATION.get(key, 0)*100}% capital")
        elif key == "snr_adx": 
            base.update(ENHANCED_SNR_ADX_CONFIG)
        elif key == "enhanced_sma": 
            base.update(ENHANCED_SMA_CONFIG)
        elif key == "super_scalper": 
            base.update(SUPER_SCALPER_CONFIG)
        elif key == "vol_mean_reversion": 
            base.update(VOL_MEAN_REVERSION_CONFIG)
        
        cfg[key] = base
    
    return cfg

STRATEGY_CONFIG = build_strategy_config()

# ── REMAINING CONFIG ────────────────────────────────────────────────────────
STRATEGY_SYMBOLS = {
    "scalper": os.getenv("SCALPER_SYMBOL", SYMBOL),
    "snr_adx": os.getenv("SNR_ADX_SYMBOL", SYMBOL),
    "emergency": os.getenv("EMERGENCY_SYMBOL", SYMBOL),
    "enhanced_sma": os.getenv("SMA_SYMBOL", SYMBOL),
    "super_scalper": os.getenv("SUPER_SCALPER_SYMBOL", SYMBOL),
    "vol_mean_reversion": os.getenv("VOL_MEAN_REVERSION_SYMBOL", SYMBOL),
}
def get_strategy_symbol(strategy_name): return STRATEGY_SYMBOLS.get(strategy_name, SYMBOL)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "False").lower() == "true"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── STARTUP SUMMARY ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*70)
    print(" HIGH-FREQUENCY SCALPER BOT v7.2 - OPTIMIZED FOR TP HITS")
    print("="*70)
    print(f"Trading: {'ENABLED' if TRADING_ENABLED else 'DISABLED'} ({'DEMO' if IS_DEMO else 'REAL'})")
    print(f"Balance: ${INITIAL_BALANCE:,.0f} | Max trade: ${MAX_TRADE_AMOUNT}")
    print(f"Max trades/day: {MAX_TRADES_PER_DAY} | Max open positions: {MAX_OPEN_POSITIONS}")
    print(f"Min Confidence: {MIN_CONFIDENCE}%")
    
    enabled_strategies = [s for s in ACTIVE_STRATEGIES if CAPITAL_ALLOCATION.get(s, 0) > 0]
    print(f"ACTIVE STRATEGIES: {', '.join(enabled_strategies)}")
    
    print("\nSCALPER OPTIMIZATIONS APPLIED:")
    scalper_config = STRATEGY_CONFIG.get("scalper", {})
    print(f"  • Risk: {scalper_config.get('risk_per_trade', 0)*100:.1f}% per trade")
    print(f"  • SL: {scalper_config.get('stop_loss_percent', 0):.1f}% | TP: {scalper_config.get('take_profit_percent', 0):.1f}%")
    print(f"  • R/R Ratio: 1.0:1 (was 2.0:1)")
    print(f"  • Trade Duration: {scalper_config.get('trade_duration', 0)}min (was 5min)")
    print(f"  • Min Confidence: {scalper_config.get('min_confidence', 0)}% (was 40%)")
    print(f"  • Min ADX: {scalper_config.get('min_adx', 0)} (was 10)")
    
    if TELEGRAM_ENABLED: 
        print("\nTelegram alerts ENABLED")
    
    print("="*70 + "\n")