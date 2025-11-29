# debug_paths.py
import os
import json
from pathlib import Path

def debug_file_locations():
    print("=== DEBUGGING FILE PATHS ===")
    
    # Path where Python is writing
    python_path = "/Users/nimoyburrowes/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/QuantumTrader/signals.json"
    
    # Paths MT5 might be looking at
    mt5_possible_paths = [
        "QuantumTrader/signals.json",  # Relative to MQL5/Files
        "MQL5/Files/QuantumTrader/signals.json",  # Alternative relative
        "/tmp/QuantumTrader/signals.json",  # Absolute
    ]
    
    print(f"📁 Python writing to: {python_path}")
    print(f"✅ Python file exists: {os.path.exists(python_path)}")
    
    if os.path.exists(python_path):
        with open(python_path, 'r') as f:
            content = json.load(f)
        print(f"📄 File content: {content}")
    
    print("\n📋 Checking directory structure:")
    wine_dir = "/Users/nimoyburrowes/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/"
    if os.path.exists(wine_dir):
        print(f"✅ Wine MT5 directory exists: {wine_dir}")
        # List files in the directory
        try:
            files = os.listdir(wine_dir)
            print(f"📂 Files in MQL5/Files/: {files}")
        except Exception as e:
            print(f"❌ Cannot list files: {e}")
    else:
        print(f"❌ Wine MT5 directory NOT found: {wine_dir}")

if __name__ == "__main__":
    debug_file_locations()