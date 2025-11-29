# config.py — QUANTUMTRADER PRO v7.3 — MAX SIGNALS + SUPER_SCALPER UNLEASHED
import os
from dotenv import load_dotenv
from typing import Dict, Any

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
IS_DEMO = TRADE_EXECUTION != "real"          # ← real = MT5 bridge ACTIVE
INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "10000"))

print(f"SCALPER MODE: {'DEMO' if IS_DEMO else 'REAL'} | TRADING={'ENABLED' if TRADING_ENABLED else 'DISABLED'}")

# ── ACTIVE STRATEGIES ───────────────────────────────────────────────────────
_active_raw = os.getenv("ACTIVE_STRATEGIES", "scalper,super_scalper")
ACTIVE_STRATEGIES = [s.strip() for s in _active_raw.split(",") if s.strip()]

# ── CAPITAL ALLOCATION ──────────────────────────────────────────────────────
CAPITAL_ALLOCATION = {
    "scalper":        float(os.getenv("SCALPER_CAPITAL_PERCENT", "60")) / 100,
    "super_scalper":  float(os.getenv("SUPER_SCALPER_CAPITAL_PERCENT", "40")) / 100,
    "emergency":      float(os.getenv("EMERGENCY_CAPITAL_PERCENT", "0")) / 100,
    "snr_adx":        0.0,
    "enhanced_sma":   0.0,
    "vol_mean_reversion": 0.0,
}

# ── GLOBAL RISK SETTINGS ────────────────────────────────────────────────────
MAX_TRADE_AMOUNT = float(os.getenv("MAX_TRADE_AMOUNT", "0.20"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "20"))
MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", "45"))

# ── SCALPER-SPECIFIC ────────────────────────────────────────────────────────
STRATEGY_RISK_PARAMS = {
    "scalper": {
        "stop_loss_percent": float(os.getenv("SCALPER_STOP_LOSS_PERCENT", "0.25")),
        "take_profit_percent": float(os.getenv("SCALPER_TAKE_PROFIT_PERCENT", "0.25")),
        "risk_per_trade": 0.02,
        "max_open_trades": 15,
    },
    "super_scalper": {
        "stop_loss_percent": 0.25,
        "take_profit_percent": 0.25,
        "risk_per_trade": 0.02,
        "max_open_trades": 10,
    },
}

# ── INDICATOR CONFIGS ───────────────────────────────────────────────────────
SCALPER_CONFIG = { 
    "rsi_period": 5,
    "bollinger_period": 10,
    "bollinger_std": 1.5,
    "ema_fast": 3,
    "ema_slow": 8,
    "min_confidence": 45,           # ← LOWERED FOR MAX SIGNALS
    "min_adx": 12,
    "max_adx": 80,
    "cooldown_seconds": 5,
}

SUPER_SCALPER_CONFIG = {
    "enabled": True,
    "min_confidence": 45,
    "stop_loss_percent": 0.25,
    "take_profit_percent": 0.25,
    "max_open_trades": 10,
    # Burst mode ready
}

# ── BUILD FINAL STRATEGY CONFIG ─────────────────────────────────────────────
def build_strategy_config():
    cfg = {}
    for key in ACTIVE_STRATEGIES:
        base = {
            "enabled": True,
            "capital": INITIAL_BALANCE * CAPITAL_ALLOCATION.get(key, 0.0),
            "risk_per_trade": STRATEGY_RISK_PARAMS.get(key, {}).get("risk_per_trade", 0.01),
            "stop_loss_percent": STRATEGY_RISK_PARAMS.get(key, {}).get("stop_loss_percent", 0.3),
            "take_profit_percent": STRATEGY_RISK_PARAMS.get(key, {}).get("take_profit_percent", 0.3),
            "max_open_trades": STRATEGY_RISK_PARAMS.get(key, {}).get("max_open_trades", 5),
            "max_trade_amount": MAX_TRADE_AMOUNT,
        }
        
        if key == "scalper":
            base.update(SCALPER_CONFIG)
            print("SCALPER ENABLED — HIGH FREQUENCY MODE")
        elif key == "super_scalper":
            base.update(SUPER_SCALPER_CONFIG)
            print("SUPER SCALPER ENABLED — BURST TRADING ACTIVE — 15–40 TRADES/HOUR")
        
        cfg[key] = base
    return cfg

STRATEGY_CONFIG = build_strategy_config()

# ── SYMBOL MAPPING ──────────────────────────────────────────────────────────
STRATEGY_SYMBOLS = {
    "scalper": os.getenv("SCALPER_SYMBOL", "Volatility 100 Index"),
    "super_scalper": os.getenv("SUPER_SCALPER_SYMBOL", "Volatility 100 Index"),
    "emergency": os.getenv("EMERGENCY_SYMBOL", "R_100"),
}
def get_strategy_symbol(strategy_name): 
    return STRATEGY_SYMBOLS.get(strategy_name, "Volatility 100 Index")

# ── TELEGRAM & SERVER ───────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "False").lower() == "true"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"