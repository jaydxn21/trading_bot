# deriv_connection.py - MODULAR, BULLETPROOF DERIV CONNECTION MANAGER
import eventlet
eventlet.monkey_patch()

import logging
import threading
import time
import json
import websocket
from typing import Callable, Dict, Any, Optional
from enum import Enum
import queue

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    ERROR = "error"

class DerivConnection:
    """
    BULLETPROOF DERIV WEBSOCKET CONNECTION MANAGER
    - Automatic reconnection with exponential backoff
    - Connection state management
    - Resilient to network issues
    - Modular and reusable
    """
    
    def __init__(self, app_id: str, token: str, is_demo: bool = True):
        self.app_id = app_id
        self.token = token.strip()
        self.is_demo = is_demo
        
        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.ws = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 1  # Start with 1 second
        
        # Callbacks
        self.message_handlers = []
        self.state_change_handlers = []
        self.error_handlers = []
        
        # Message queue for sending
        self.message_queue = queue.Queue()
        
        # Track if we should be running
        self.running = False
        
        logger.info(f"DerivConnection initialized: Demo={is_demo}, AppID={app_id}")
    
    def add_message_handler(self, handler: Callable):
        """Add handler for incoming messages"""
        self.message_handlers.append(handler)
    
    def add_state_change_handler(self, handler: Callable):
        """Add handler for state changes"""
        self.state_change_handlers.append(handler)
    
    def add_error_handler(self, handler: Callable):
        """Add handler for errors"""
        self.error_handlers.append(handler)
    
    def _change_state(self, new_state: ConnectionState, message: str = ""):
        """Update connection state and notify handlers"""
        old_state = self.state
        self.state = new_state
        
        logger.info(f"Connection state: {old_state.value} → {new_state.value} {message}")
        
        for handler in self.state_change_handlers:
            try:
                handler(old_state, new_state, message)
            except Exception as e:
                logger.error(f"State change handler error: {e}")
    
    def _handle_error(self, error: str, critical: bool = False):
        """Handle errors and notify handlers"""
        logger.error(f"Connection error: {error}")
        
        for handler in self.error_handlers:
            try:
                handler(error, critical)
            except Exception as e:
                logger.error(f"Error handler error: {e}")
    
    def _websocket_on_open(self, ws):
        """WebSocket on_open callback"""
        self.ws = ws
        self.reconnect_attempts = 0
        self.reconnect_delay = 1
        
        if self.is_demo:
            logger.info("Demo mode - skipping authentication")
            self._change_state(ConnectionState.AUTHENTICATED, "Demo mode")
            return
        
        self._change_state(ConnectionState.AUTHENTICATING, "Sending auth...")
        
        # Send authentication
        auth_message = {"authorize": self.token}
        self._send_message(auth_message)
        
        # Set authentication timeout
        threading.Timer(15.0, self._check_auth_timeout).start()
    
    def _websocket_on_message(self, ws, message):
        """WebSocket on_message callback"""
        try:
            data = json.loads(message)
            msg_type = data.get("msg_type")
            
            # Handle authentication response
            if msg_type == "authorization":
                self._handle_auth_response(data)
            elif msg_type == "tick":
                self._handle_tick(data)
            elif msg_type == "candles":
                self._handle_candles(data)
            elif msg_type in ["buy", "proposal_open_contract"]:
                self._handle_trade_response(data)
            elif msg_type == "contract_update":
                self._handle_contract_update(data)
            elif msg_type == "balance":
                self._handle_balance(data)
            
            # Pass to all message handlers
            for handler in self.message_handlers:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Message handler error: {e}")
                    
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Message processing error: {e}")
    
    def _websocket_on_error(self, ws, error):
        """WebSocket on_error callback"""
        self._handle_error(f"WebSocket error: {error}")
    
    def _websocket_on_close(self, ws, close_status_code, close_msg):
        """WebSocket on_close callback"""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self._change_state(ConnectionState.DISCONNECTED, "Connection closed")
        
        if self.running:
            self._schedule_reconnect()
    
    def _handle_auth_response(self, data):
        """Handle authentication response"""
        auth = data.get("authorization", {})
        error = data.get("error", {})
        
        if auth.get("token"):
            self._change_state(ConnectionState.AUTHENTICATED, "Authentication successful")
            logger.info("✅ Successfully authenticated with Deriv")
        else:
            error_code = error.get("code", "UNKNOWN")
            error_message = error.get("message", "Authentication failed")
            self._change_state(ConnectionState.ERROR, f"Auth failed: {error_code}")
            self._handle_error(f"Authentication failed: {error_code} - {error_message}", critical=True)
    
    def _handle_tick(self, data):
        """Handle tick data"""
        # Basic tick handling - extend as needed
        tick = data.get("tick", {})
        if tick.get("quote"):
            pass  # Handled by message handlers
    
    def _handle_candles(self, data):
        """Handle candle data"""
        # Basic candle handling - extend as needed
        pass
    
    def _handle_trade_response(self, data):
        """Handle trade responses"""
        # Basic trade response handling
        pass
    
    def _handle_contract_update(self, data):
        """Handle contract updates"""
        # Basic contract update handling
        pass
    
    def _handle_balance(self, data):
        """Handle balance updates"""
        # Basic balance handling
        pass
    
    def _check_auth_timeout(self):
        """Check if authentication has timed out"""
        if self.state == ConnectionState.AUTHENTICATING:
            self._handle_error("Authentication timeout - token may be invalid", critical=True)
            self._change_state(ConnectionState.ERROR, "Authentication timeout")
    
    def _send_message(self, message: Dict):
        """Safely send message through WebSocket"""
        if self.ws and self.state in [ConnectionState.AUTHENTICATED, ConnectionState.AUTHENTICATING]:
            try:
                self.ws.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                self._handle_error(f"Send message failed: {e}")
        else:
            # Queue message if not ready
            self.message_queue.put(message)
    
    def _process_message_queue(self):
        """Process queued messages when connection is ready"""
        while not self.message_queue.empty() and self.state == ConnectionState.AUTHENTICATED:
            try:
                message = self.message_queue.get_nowait()
                self._send_message(message)
            except queue.Empty:
                break
    
    def _schedule_reconnect(self):
        """Schedule reconnection with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            self._handle_error("Max reconnection attempts reached", critical=True)
            return
        
        delay = min(self.reconnect_delay * (2 ** self.reconnect_attempts), 60)  # Max 60 seconds
        self.reconnect_attempts += 1
        
        logger.info(f"Scheduling reconnect in {delay} seconds (attempt {self.reconnect_attempts})")
        threading.Timer(delay, self.connect).start()
    
    def connect(self):
        """Establish WebSocket connection"""
        if self.running and self.state in [ConnectionState.CONNECTING, ConnectionState.CONNECTED]:
            logger.warning("Already connected or connecting")
            return
        
        self.running = True
        self._change_state(ConnectionState.CONNECTING, "Starting connection...")
        
        try:
            # WebSocket configuration
            self.ws = websocket.WebSocketApp(
                f"wss://ws.derivws.com/websockets/v3?app_id={self.app_id}",
                on_open=self._websocket_on_open,
                on_message=self._websocket_on_message,
                on_error=self._websocket_on_error,
                on_close=self._websocket_on_close
            )
            
            # Start WebSocket in separate thread
            def run_websocket():
                self.ws.run_forever(
                    ping_interval=30,
                    ping_timeout=10,
                    reconnect=5  # Internal reconnect attempts
                )
            
            websocket_thread = threading.Thread(target=run_websocket, daemon=True)
            websocket_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket: {e}")
            self._change_state(ConnectionState.ERROR, f"Connection failed: {e}")
            self._schedule_reconnect()
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        self.running = False
        if self.ws:
            self.ws.close()
        self._change_state(ConnectionState.DISCONNECTED, "Manual disconnect")
    
    def subscribe_ticks(self, symbol: str):
        """Subscribe to tick data"""
        message = {
            "ticks": symbol,
            "subscribe": 1
        }
        self._send_message(message)
    
    def subscribe_candles(self, symbol: str, granularity: int = 60, count: int = 100):
        """Subscribe to candle data"""
        message = {
            "ticks_history": symbol,
            "end": "latest",
            "count": count,
            "granularity": granularity,
            "style": "candles",
            "subscribe": 1
        }
        self._send_message(message)
    
    def get_balance(self):
        """Request balance update"""
        message = {"balance": 1}
        self._send_message(message)
    
    def place_trade(self, symbol: str, contract_type: str, amount: float, duration: int = 5):
        """Place a trade"""
        message = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "contract_type": contract_type.upper(),
                "symbol": symbol,
                "duration": duration,
                "duration_unit": "t",
                "basis": "stake",
                "amount": amount
            }
        }
        self._send_message(message)
    
    def is_connected(self) -> bool:
        """Check if connection is active and authenticated"""
        return self.state == ConnectionState.AUTHENTICATED or (self.is_demo and self.state == ConnectionState.CONNECTED)
    
    def get_state(self) -> ConnectionState:
        """Get current connection state"""
        return self.state