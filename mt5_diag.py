# mt5_path_diagnostic.py
import os
import json
from pathlib import Path

def diagnose_mt5_paths():
    print("=== MT5 PATH DIAGNOSTIC ===")
    
    # Path where Python is writing
    python_path = os.path.expanduser("~/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/QuantumTrader/signals.json")
    
    print(f"📁 Python writing to: {python_path}")
    print(f"✅ Python file exists: {os.path.exists(python_path)}")
    
    if os.path.exists(python_path):
        with open(python_path, 'r') as f:
            content = json.load(f)
        print(f"📄 Current signal content: {content}")
    
    # Check directory structure
    wine_dir = os.path.expanduser("~/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/")
    if os.path.exists(wine_dir):
        print(f"✅ Wine MT5 directory exists: {wine_dir}")
        try:
            files = os.listdir(wine_dir)
            print(f"📂 Files in MQL5/Files/: {files}")
            
            quantum_dir = os.path.join(wine_dir, "QuantumTrader")
            if os.path.exists(quantum_dir):
                quantum_files = os.listdir(quantum_dir)
                print(f"📂 Files in QuantumTrader/: {quantum_files}")
            else:
                print("❌ QuantumTrader directory not found in MQL5/Files/")
                
        except Exception as e:
            print(f"❌ Cannot list files: {e}")
    else:
        print(f"❌ Wine MT5 directory NOT found: {wine_dir}")
    
    print("\n🔍 PATHS MT5 MIGHT BE LOOKING AT:")
    
    # Common MT5 paths to check
    mt5_paths = [
        "C:/Program Files/MetaTrader 5/MQL5/Files/QuantumTrader/signals.json",
        "QuantumTrader/signals.json", 
        "MQL5/Files/QuantumTrader/signals.json",
        "Files/QuantumTrader/signals.json"
    ]
    
    for path in mt5_paths:
        # Check if this corresponds to our Python path
        print(f"• {path}")
    
    print(f"\n💡 RECOMMENDATION: Use 'QuantumTrader/signals.json' in MT5 EA")

if __name__ == "__main__":
    diagnose_mt5_paths()