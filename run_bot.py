# run_bot.py - Main launcher for the complete trading system
import threading
import time
import logging
from server import run_server
from bot import run_deriv_ws
import config  # Import config to show settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_config_summary():
    """Print configuration summary at startup."""
    logger.info("🚀 QuantumTrader Pro - V100 Optimized")
    logger.info(f"📊 Active Strategies: {', '.join(config.ACTIVE_STRATEGIES)}")
    logger.info(f"🎯 Strategy Aliases: {config.STRATEGY_ALIASES}")
    logger.info(f"💰 Initial Balance: ${config.INITIAL_BALANCE}")
    logger.info(f"⚡ Trading Enabled: {config.TRADING_ENABLED}")
    logger.info(f"📈 V100 Optimizations: ADX>{config.V100_OPTIMIZED['min_adx']}, Volume>{config.V100_OPTIMIZED['min_volume_ratio']:.1f}")
    logger.info(f"🎪 Optimal Hours: {[f'{p['start'].strftime('%H:%M')}-{p['end'].strftime('%H:%M')}' for p in config.V100_OPTIMIZED['optimal_hours']]}")
    logger.info(f"🛡️ Risk Management: {config.RISK_PER_TRADE*100}% per trade, Stop Loss: {config.STOP_LOSS_PERCENT}%")

def start_system():
    """Start the complete trading system."""
    print_config_summary()
    
    # Start frontend WebSocket server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    logger.info("⏳ Waiting for frontend server to start...")
    time.sleep(3)
    
    # Start the main trading bot
    logger.info("🤖 Starting V100 Optimized Trading Bot...")
    
    # Run trading bot in main thread (it will handle its own threading)
    try:
        run_deriv_ws()
    except KeyboardInterrupt:
        logger.info("👋 Received interrupt signal - shutting down")
    except Exception as e:
        logger.error(f"❌ Trading bot crashed: {e}")
        logger.info("🔄 Restarting system in 10 seconds...")
        time.sleep(10)
        start_system()

if __name__ == "__main__":
    start_system()