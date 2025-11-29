# final_test.py
import json
import os
import time
from datetime import datetime
from pathlib import Path

def test_complete_bridge():
    signal_file = "/tmp/QuantumTrader/signals.json"
    
    # Create signal
    signal = {
        "symbol": "Volatility 100 Index",
        "action": "BUY",
        "price": "100.50000",
        "sl_price": "99.70000",
        "tp_price": "101.30000",
        "timestamp": datetime.now().isoformat()
    }
    
    print("=== TESTING COMPLETE BRIDGE ===")
    print("Creating signal at:", datetime.now().isoformat())
    
    # Ensure directory exists
    Path("/tmp/QuantumTrader").mkdir(parents=True, exist_ok=True)
    
    # Write signal
    with open(signal_file, 'w') as f:
        json.dump(signal, f, indent=2)
    
    print("✅ Signal created!")
    print("📋 Signal content:")
    print(json.dumps(signal, indent=2))
    
    # Monitor for 30 seconds
    print("\n🔍 Monitoring for MT5 response...")
    for i in range(30):
        time.sleep(1)
        if not os.path.exists(signal_file):
            print(f"🎯 SUCCESS! MT5 processed the signal at {datetime.now().isoformat()}")
            return True
        if i % 5 == 0:
            print(f"⏰ Still waiting... {i+1}s elapsed")
    
    print("❌ Signal not processed within 30 seconds")
    return False

if __name__ == "__main__":
    test_complete_bridge()