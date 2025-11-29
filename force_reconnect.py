#!/usr/bin/env python3
import sys
import os
import json
import time
sys.path.insert(0, os.path.dirname(__file__))

print("🔄 FORCING WEBSOCKET RECONNECTION")
print("=" * 40)

try:
    from bot import trading_bot
    import config
    
    print("🔧 Resetting connection state...")
    
    # Reset connection states
    trading_bot.deriv_connected = False
    trading_bot.authorized = False
    trading_bot.subscribed = False
    trading_bot.candles = []
    
    print("✅ Reset connection states")
    print("🔄 Restarting Deriv connection...")
    
    # Restart the connection
    trading_bot.start_deriv_connection()
    
    print("⏳ Waiting 10 seconds for connection...")
    time.sleep(10)
    
    # Check status again
    print("📡 POST-RECONNECTION STATUS:")
    print(f"   WebSocket connected: {trading_bot.deriv_connected}")
    print(f"   Authorized: {trading_bot.authorized}")
    print(f"   Subscribed: {trading_bot.subscribed}")
    
    if trading_bot.deriv_connected and trading_bot.authorized:
        print("✅ Connection successful!")
        print("📊 Waiting for tick data...")
    else:
        print("❌ Connection failed - may need bot restart")
        
except Exception as e:
    print(f"❌ Error: {e}")
