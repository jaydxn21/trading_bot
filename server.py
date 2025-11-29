# server_simple.py - Synchronous version using Flask
from flask import Flask
from flask_socketio import SocketIO, emit
import logging
from datetime import datetime
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

class TradingServer:
    def __init__(self):
        self.connected_clients = 0
        self.trading_bot_thread = None
        self.last_candle = None
        self.last_signals = []
        self.system_status = {
            'trading_enabled': True,
            'connection_status': 'connected'
        }

    def start_trading_bot(self):
        """Start the trading bot in a separate thread."""
        def run_bot():
            try:
                from bot import run_deriv_ws
                run_deriv_ws()
            except Exception as e:
                logger.error("Trading bot error: %s", e)
                
        self.trading_bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.trading_bot_thread.start()
        logger.info("Trading bot started")

    def broadcast_trading_cycle(self, signal_data):
        """Broadcast trading cycle information to all clients."""
        try:
            socketio.emit('trading_cycle', signal_data)
            logger.info("Broadcast trading cycle: %s", signal_data.get('strategy', 'unknown'))
        except Exception as e:
            logger.error("Error broadcasting trading cycle: %s", e)

    def broadcast_candle_update(self, candle_data):
        """Broadcast candle updates to all clients."""
        try:
            socketio.emit('candle_update', candle_data)
        except Exception as e:
            logger.error("Error broadcasting candle update: %s", e)

    def broadcast_system_summary(self, summary_data):
        """Broadcast system summary updates."""
        try:
            socketio.emit('system_summary', summary_data)
        except Exception as e:
            logger.error("Error broadcasting system summary: %s", e)

# Global server instance
trading_server = TradingServer()

@socketio.on('connect')
def handle_connect():
    trading_server.connected_clients += 1
    logger.info("Client connected. Total clients: %s", trading_server.connected_clients)
    
    # Send initial data
    emit('connection', {
        'status': 'connected',
        'message': 'Connected to Trading Bot Server',
        'timestamp': datetime.now().isoformat()
    })
    
    emit('trading_status', {
        'enabled': trading_server.system_status['trading_enabled'],
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    trading_server.connected_clients -= 1
    logger.info("Client disconnected. Total clients: %s", trading_server.connected_clients)

@socketio.on('trading_control')
def handle_trading_control(data):
    enabled = data.get('enabled', True)
    trading_server.system_status['trading_enabled'] = enabled
    logger.info("Trading control: %s", 'ENABLED' if enabled else 'DISABLED')
    
    emit('trading_status', {
        'enabled': enabled,
        'timestamp': datetime.now().isoformat()
    }, broadcast=True)

@socketio.on('request_data')
def handle_request_data(data):
    data_type = data.get('data_type')
    if data_type == 'system_summary':
        # Send sample system summary
        emit('system_summary', {
            'portfolio': {
                'balance': 10000,
                'equity': 10000,
                'initialBalance': 10000,
                'floating_pnl': 0
            },
            'open_trades': [],
            'performance': {
                'summary': {
                    'total_trades': 0,
                    'win_rate': 0,
                    'total_profit': 0,
                    'current_equity': 10000,
                    'open_positions': 0,
                    'consecutive_losses': 0
                }
            },
            'timestamp': datetime.now().isoformat()
        })
    elif data_type == 'historical_candles':
        # Send sample historical candles
        candles = []
        base_price = 100.0
        current_time = int(datetime.now().timestamp()) - 3600
        
        for i in range(100):
            open_price = base_price + (i * 0.1)
            close_price = open_price + (0.5 if i % 2 == 0 else -0.3)
            high_price = max(open_price, close_price) + 0.2
            low_price = min(open_price, close_price) - 0.2
            
            candles.append({
                'time': current_time + (i * 60),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': 1000
            })
        
        emit('candles', candles)

def run_server():
    """Run the server."""
    logger.info("Starting WebSocket server on http://0.0.0.0:5000")
    trading_server.start_trading_bot()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    run_server()