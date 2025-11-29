# mt5_bridge.py - macOS Wine compatible
import json
import os
import logging
from datetime import datetime
from pathlib import Path

class MT5Bridge:
    def __init__(self):
        self.setup_logging()
        # Use the Wine MT5 Files directory that we confirmed works
        self.signal_file = os.path.expanduser("~/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/QuantumTrader/signals.json")
        self._ensure_directory()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/tmp/quantum_trader_bridge.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _ensure_directory(self):
        """Ensure the QuantumTrader directory exists in Wine MT5 Files"""
        directory = os.path.dirname(self.signal_file)
        Path(directory).mkdir(parents=True, exist_ok=True)
        self.logger.info(f"📁 Using Wine MT5 directory: {directory}")
        
        # Verify we can write
        test_file = os.path.join(directory, "test.txt")
        try:
            with open(test_file, 'w') as f:
                f.write("Python bridge test - " + datetime.now().isoformat())
            os.remove(test_file)
            self.logger.info("✅ Python can write to Wine MT5 directory")
        except Exception as e:
            self.logger.error(f"❌ Python cannot write to Wine directory: {e}")
    
    def create_signal(self, symbol, action, price, sl_price=None, tp_price=None):
        """Create trading signal in Wine MT5 Files directory"""
        if sl_price is None:
            sl_price = price * 0.997  # 0.3% SL
        if tp_price is None:
            tp_price = price * 1.003  # 0.3% TP
            
        signal = {
            "symbol": symbol,
            "action": action.upper(),
            "price": f"{price:.5f}",
            "sl_price": f"{sl_price:.5f}",
            "tp_price": f"{tp_price:.5f}",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            with open(self.signal_file, 'w') as f:
                json.dump(signal, f, indent=2)
            
            self.logger.info(f"✅ Signal created: {action} {symbol} @ {price}")
            self.logger.info(f"📍 File: {self.signal_file}")
            
            # Verify file was created
            if os.path.exists(self.signal_file):
                with open(self.signal_file, 'r') as f:
                    content = json.load(f)
                self.logger.info(f"📄 Content: {content}")
                
                # Also log the relative path MT5 should use
                self.logger.info("💡 MT5 EA should use: QuantumTrader/signals.json")
                return True
            else:
                self.logger.error("❌ Signal file was not created!")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to create signal: {e}")
            return False
    
    def clear_signal(self):
        """Clear the signal file"""
        try:
            if os.path.exists(self.signal_file):
                os.remove(self.signal_file)
                self.logger.info("🗑️ Signal file cleared")
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Failed to clear signal: {e}")
            return False
    
    def get_signal_info(self):
        """Get current signal file information"""
        try:
            if os.path.exists(self.signal_file):
                with open(self.signal_file, 'r') as f:
                    signal = json.load(f)
                return {
                    'file_path': self.signal_file,
                    'file_size': os.path.getsize(self.signal_file),
                    'signal': signal,
                    'exists': True
                }
            else:
                return {
                    'file_path': self.signal_file,
                    'exists': False
                }
        except Exception as e:
            self.logger.error(f"❌ Error reading signal info: {e}")
            return None
    
    def get_mt5_path_hint(self):
        """Get the path hint for MT5 EA"""
        return "QuantumTrader/signals.json"

# Global instance
mt5_bridge = MT5Bridge()

# Test functions
def test_bridge():
    """Test the MT5 bridge"""
    print("=== Testing MT5 Wine Bridge ===")
    
    bridge = MT5Bridge()
    
    # Create a test signal
    success = bridge.create_signal(
        symbol="Volatility 100 Index",
        action="BUY",
        price=100.50
    )
    
    if success:
        print("✅ Bridge test PASSED")
        print(f"📁 Wine path: {bridge.signal_file}")
        print(f"💡 MT5 should use: {bridge.get_mt5_path_hint()}")
        
        # Show signal info
        signal_info = bridge.get_signal_info()
        if signal_info and signal_info['exists']:
            print(f"📋 Signal data: {signal_info['signal']}")
        
        # Test clearing
        bridge.clear_signal()
        print("✅ Signal cleared")
    else:
        print("❌ Bridge test FAILED")

def create_trading_signal(symbol, action, price, sl_price=None, tp_price=None):
    """Convenience function to create trading signals"""
    bridge = MT5Bridge()
    return bridge.create_signal(symbol, action, price, sl_price, tp_price)

def monitor_signal_processing():
    """Create a signal and monitor if MT5 processes it"""
    print("=== Monitoring Signal Processing ===")
    
    bridge = MT5Bridge()
    
    # Clear any existing signal
    bridge.clear_signal()
    
    # Create new signal
    success = bridge.create_signal(
        symbol="Volatility 100 Index",
        action="BUY", 
        price=100.50
    )
    
    if not success:
        print("❌ Failed to create signal")
        return False
    
    print("✅ Signal created - waiting for MT5 to process...")
    print("If MT5 EA is working, it should detect and delete the signal file")
    
    import time
    for i in range(30):  # Monitor for 30 seconds
        time.sleep(1)
        if not os.path.exists(bridge.signal_file):
            print(f"🎯 SUCCESS! MT5 processed the signal at {i+1} seconds")
            return True
        if i % 5 == 0:
            print(f"⏰ Still waiting... {i+1}s elapsed")
    
    print("❌ MT5 did not process signal within 30 seconds")
    return False

if __name__ == "__main__":
    # Run comprehensive test
    test_bridge()
    print("\n" + "="*50)
    monitor_signal_processing()