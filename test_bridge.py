# test_bridge.py
import json
import os
from datetime import datetime

def create_test_signal():
    """Create a test signal file"""
    signal = {
        "symbol": "Volatility 100 Index",
        "action": "BUY",
        "price": "100.50000",
        "sl_price": "99.70000",
        "tp_price": "100.30000",
        "timestamp": datetime.now().isoformat()
    }
    
    signal_file = "/tmp/QuantumTrader/signals.json"
    
    try:
        os.makedirs(os.path.dirname(signal_file), exist_ok=True)
        with open(signal_file, 'w') as f:
            json.dump(signal, f, indent=2)
        
        print(f"✅ Test signal created: {signal_file}")
        
        # Verify
        with open(signal_file, 'r') as f:
            content = json.load(f)
        print(f"✅ Signal content: {content}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    create_test_signal()