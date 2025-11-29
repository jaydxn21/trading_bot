# deriv_trading.py - Real Deriv API trading execution
import json
import websocket
import logging
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

class DerivTrading:
    def __init__(self, api_token: str, app_id: int = 1089):
        self.api_token = api_token
        self.app_id = app_id
        self.ws_url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        self.websocket: Optional[websocket.WebSocketApp] = None
        self.connected = False
        self.authorized = False
        self.balance: Optional[float] = None
        self.last_balance_update = None
        self.connection_lock = threading.Lock()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.message_handlers: Dict[str, Callable] = {}
        self.bot_instance = None  # Reference to main bot for callbacks
        
    def connect(self) -> bool:
        """Connect to Deriv WebSocket with proper reconnection handling"""
        with self.connection_lock:
            if self.connected and self.authorized:
                logger.info("✅ Already connected and authorized to Deriv")
                return True
                
            try:
                logger.info("🔌 Connecting to Deriv Real Trading API...")
                
                self.websocket = websocket.WebSocketApp(
                    self.ws_url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open
                )
                
                # Run WebSocket in separate thread
                ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
                ws_thread.start()
                
                # Wait for connection with timeout
                for i in range(20):  # 20 second timeout
                    if self.connected and self.authorized:
                        logger.info("✅ Successfully connected and authorized with Deriv")
                        self.reconnect_attempts = 0
                        return True
                    time.sleep(1)
                
                logger.error("❌ Deriv connection timeout")
                return False
                
            except Exception as e:
                logger.error(f"❌ Deriv real trading connection failed: {e}")
                return False
    
    def _run_websocket(self):
        """Run WebSocket with reconnection logic"""
        try:
            self.websocket.run_forever(
                ping_interval=30,
                ping_timeout=10,
                reconnect=5  # Auto-reconnect up to 5 times
            )
        except Exception as e:
            logger.error(f"WebSocket run forever error: {e}")
    
    def _on_open(self, ws):
        """WebSocket connection opened"""
        logger.info("✅ WebSocket connected to Deriv Real Trading")
        self.connected = True
        self.reconnect_attempts = 0
        
        # Authorize with API token
        auth_msg = {"authorize": self.api_token}
        try:
            ws.send(json.dumps(auth_msg))
        except Exception as e:
            logger.error(f"❌ Failed to send auth message: {e}")
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            msg = json.loads(message)
            logger.debug(f"📨 Deriv API response: {msg}")
            
            # Handle authorization response
            if "authorize" in msg:
                self._handle_authorize(msg["authorize"])
            
            # Handle buy contract response
            elif "buy" in msg:
                self._handle_buy_response(msg["buy"])
            
            # Handle explicit balance response
            elif "balance" in msg:
                self._handle_balance_response(msg["balance"])
                
            # Handle proposal response
            elif "proposal" in msg:
                self._handle_proposal_response(msg["proposal"])
                
        except Exception as e:
            logger.error(f"❌ Error processing Deriv message: {e}")
            logger.error(f"📄 Problematic message: {message}")
    
    def _handle_authorize(self, auth_response):
        """Handle authorization response"""
        if isinstance(auth_response, dict):
            if auth_response.get("error"):
                error_msg = auth_response["error"]["message"]
                logger.error(f"❌ Deriv authorization failed: {error_msg}")
                self.authorized = False
            else:
                self.authorized = True
                logger.info("✅ Authorized with Deriv Real Account")
                
                # Extract balance from proper location
                account_info = auth_response.get("account", {})
                self.balance = float(account_info.get("balance", 0))
                logger.info(f"💰 Real Account Balance: ${self.balance:.2f}")
                
                # Broadcast balance update
                self._broadcast_balance_update()
    
    def _handle_buy_response(self, buy_response):
        """Handle buy contract response"""
        if isinstance(buy_response, dict):
            if buy_response.get("error"):
                error_msg = buy_response["error"]["message"]
                logger.error(f"❌ Real trade failed: {error_msg}")
            else:
                contract_id = buy_response.get("contract_id", "Unknown")
                logger.info(f"✅ REAL TRADE CONFIRMED - Contract ID: {contract_id}")
                
                # Update balance after successful trade
                time.sleep(1)
                self.get_balance()
    
    def _handle_balance_response(self, balance_response):
        """Handle balance response"""
        if isinstance(balance_response, dict) and "balance" in balance_response:
            self.balance = float(balance_response["balance"])
        elif isinstance(balance_response, (int, float)):
            self.balance = float(balance_response)
        
        self.last_balance_update = datetime.now()
        logger.info(f"💰 Updated Real Balance: ${self.balance:.2f}")
        self._broadcast_balance_update()
    
    def _handle_proposal_response(self, proposal_response):
        """Handle proposal response for contract verification"""
        if isinstance(proposal_response, dict) and proposal_response.get("error"):
            logger.error(f"❌ Contract proposal error: {proposal_response['error']['message']}")
    
    def _broadcast_balance_update(self):
        """Broadcast balance update to dashboard"""
        try:
            if self.bot_instance:
                self.bot_instance.broadcast_real_trade_status({
                    'type': 'balance_update',
                    'real_balance': self.balance,
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Error broadcasting balance update: {e}")
    
    def _on_error(self, ws, error):
        logger.error(f"❌ Deriv WebSocket error: {error}")
        self.connected = False
        self.authorized = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"🔌 Deriv connection closed: {close_msg}")
        self.connected = False
        self.authorized = False
        
        # Attempt reconnection if not manually closed
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"🔄 Attempting reconnect ({self.reconnect_attempts}/{self.max_reconnect_attempts})...")
            time.sleep(5)
            self.connect()
    
    def place_trade(self, symbol: str, amount: float, direction: str, 
                   duration: int = 5, duration_unit: str = "m") -> bool:
        """Place a REAL trade on Deriv platform with validation"""
        if not self.connected or not self.authorized:
            logger.error("❌ Not connected/authorized to Deriv Real Trading")
            if not self.connect():
                return False
        
        # Validate trade parameters
        if amount <= 0:
            logger.error("❌ Invalid trade amount")
            return False
        
        if direction.upper() not in ["CALL", "PUT"]:
            logger.error("❌ Invalid trade direction")
            return False
        
        # Check if we have sufficient balance
        if self.balance and amount > self.balance:
            logger.error(f"❌ Insufficient balance: ${amount:.2f} > ${self.balance:.2f}")
            return False
        
        trade_request = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": direction.upper(),
                "currency": "USD",
                "duration": duration,
                "duration_unit": duration_unit,
                "symbol": symbol
            }
        }
        
        try:
            self.websocket.send(json.dumps(trade_request))
            logger.info(f"🚀 Placing REAL {direction} trade: ${amount} on {symbol}")
            return True
        except Exception as e:
            logger.error(f"❌ Real trade placement failed: {e}")
            # Attempt reconnection on failure
            self.connect()
            return False
    
    def get_balance(self) -> Optional[float]:
        """Get REAL account balance with reconnection"""
        if not self.connected or not self.authorized:
            if not self.connect():
                return None
        
        balance_request = {"balance": 1}
        try:
            self.websocket.send(json.dumps(balance_request))
            # Balance will be updated via _on_message callback
            return self.balance
        except Exception as e:
            logger.error(f"❌ Real balance request failed: {e}")
            return None
    
    def verify_symbol(self, symbol: str) -> bool:
        """Verify if symbol is available for trading"""
        if not self.connected or not self.authorized:
            return False
            
        proposal_request = {
            "proposal": 1,
            "subscribe": 0,
            "amount": 1,
            "basis": "payout",
            "contract_type": "CALL",
            "currency": "USD",
            "duration": 1,
            "duration_unit": "m",
            "symbol": symbol
        }
        
        try:
            self.websocket.send(json.dumps(proposal_request))
            return True
        except Exception as e:
            logger.error(f"❌ Symbol verification failed: {e}")
            return False
    
    def disconnect(self):
        """Close Deriv connection"""
        self.reconnect_attempts = self.max_reconnect_attempts  # Prevent auto-reconnect
        if self.websocket:
            self.websocket.close()
        self.connected = False
        self.authorized = False
    
    def set_bot_instance(self, bot_instance):
        """Set reference to main bot instance for callbacks"""
        self.bot_instance = bot_instance
    
    def get_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return {
            "connected": self.connected,
            "authorized": self.authorized,
            "balance": self.balance,
            "last_balance_update": self.last_balance_update.isoformat() if self.last_balance_update else None,
            "reconnect_attempts": self.reconnect_attempts
        }