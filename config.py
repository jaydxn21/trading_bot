# config.py — QUANTUMTRADER PRO v7.3 — Clean Modular Version
import os
from dotenv import load_dotenv

load_dotenv()

# ── API & SYMBOL ─────────────────────────────────────────────────────────────
APP_ID = os.getenv("APP_ID", "111074")
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise ValueError("API_TOKEN is missing! Add it to your .env file.")

SYMBOL = os.getenv("SYMBOL", "R_100")
GRANULARITY = int(os.getenv("GRANULARITY", "60"))  # candle interval in seconds
HISTORY_COUNT = int(os.getenv("HISTORY_COUNT", "100"))

# ── TRADING MODE ────────────────────────────────────────────────────────────
TRADING_ENABLED = os.getenv("TRADING_ENABLED", "False").lower() == "true"
TRADE_EXECUTION = os.getenv("TRADE_EXECUTION", "demo").lower()
IS_DEMO = TRADE_EXECUTION != "real"
INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "10000"))

# ── ACTIVE STRATEGIES ───────────────────────────────────────────────────────
ACTIVE_STRATEGIES = [
    s.strip() for s in os.getenv("ACTIVE_STRATEGIES", "scalper,super_scalper").split(",") if s.strip()
]

# ── CAPITAL ALLOCATION ──────────────────────────────────────────────────────
CAPITAL_ALLOCATION = {
    "scalper": float(os.getenv("SCALPER_CAPITAL_PERCENT", "60")) / 100,
    "super_scalper": float(os.getenv("SUPER_SCALPER_CAPITAL_PERCENT", "40")) / 100,
}

# ── NUKE MODE ────────────────────────────────────────────────────────────────
NUKE_MODE = os.getenv("NUKE_MODE", "False").lower() == "true"

if NUKE_MODE:
    MIN_CONFIDENCE = 30
    MAX_TRADE_AMOUNT = 0.50
    TRADE_COOLDOWN = 2
else:
    MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", "45"))
    MAX_TRADE_AMOUNT = float(os.getenv("MAX_TRADE_AMOUNT", "0.2"))
    TRADE_COOLDOWN = 5

# ── SCALPER STRATEGY CONFIG ─────────────────────────────────────────────────
SCALPER_CONFIG = {
    "enabled": True,
    "rsi_period": 5,
    "bollinger_period": 10,
    "bollinger_std": 1.5,
    "ema_fast": 3,
    "ema_slow": 8,
    "min_confidence": MIN_CONFIDENCE,
    "min_adx": 12,
    "max_adx": 80,
    "cooldown_seconds": TRADE_COOLDOWN,
    "stop_loss_percent": float(os.getenv("SCALPER_STOP_LOSS_PERCENT", "0.25")),
    "take_profit_percent": float(os.getenv("SCALPER_TAKE_PROFIT_PERCENT", "0.25")),
    "max_open_trades": int(os.getenv("SCALPER_MAX_OPEN_TRADES", "15")),
    "capital": INITIAL_BALANCE * CAPITAL_ALLOCATION.get("scalper", 0.0),
}

SUPER_SCALPER_CONFIG = {
    "enabled": True,
    "min_confidence": MIN_CONFIDENCE,
    "stop_loss_percent": 0.25,
    "take_profit_percent": 0.25,
    "max_open_trades": 10,
    "capital": INITIAL_BALANCE * CAPITAL_ALLOCATION.get("super_scalper", 0.0),
}

STRATEGY_CONFIG = {
    "scalper": SCALPER_CONFIG,
    "super_scalper": SUPER_SCALPER_CONFIG,
}

# ── SYMBOL MAPPING ──────────────────────────────────────────────────────────
STRATEGY_SYMBOLS = {
    "scalper": os.getenv("SCALPER_SYMBOL", "Volatility 100 Index"),
    "super_scalper": os.getenv("SUPER_SCALPER_SYMBOL", "Volatility 100 Index"),
}

def get_strategy_symbol(strategy_name):
    return STRATEGY_SYMBOLS.get(strategy_name, SYMBOL)


# ===================== TEST MODE ======================
TEST_MODE = True               # Turn ON/OFF advanced test mode
TEST_MODE_TYPE = "random"      # manual / cycle / random / off

# For manual:
TEST_ACTION = "BUY"            # BUY / SELL / HOLD

# For cycle mode:
TEST_CYCLE = ["BUY", "SELL", "HOLD"]
TEST_CYCLE_INDEX = 0

# For random mode:
TEST_RANDOM_WEIGHTS = {
    "BUY": 0.33,
    "SELL": 0.33,
    "HOLD": 0.34
}

# Deterministic test prices
TEST_PRICE_ENABLED = True
TEST_PRICE_VALUE = 999.99


# ── TELEGRAM / SERVER ───────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "False").lower() == "true"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
