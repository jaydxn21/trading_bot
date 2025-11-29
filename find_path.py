# find_wine_paths.py
import os
import subprocess
from pathlib import Path

def find_wine_mt5_paths():
    print("=== FINDING WINE MT5 PATHS ===")
    
    # Common Wine MT5 installation paths
    possible_paths = [
        "~/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/",
        "~/.wine/dosdevices/c:/Program Files/MetaTrader 5/MQL5/Files/",
        "~/.wine/drive_c/Program Files (x86)/MetaTrader 5/MQL5/Files/",
    ]
    
    for path in possible_paths:
        expanded_path = os.path.expanduser(path)
        print(f"\n🔍 Checking: {expanded_path}")
        print(f"   Exists: {os.path.exists(expanded_path)}")
        
        if os.path.exists(expanded_path):
            # List contents
            try:
                files = os.listdir(expanded_path)
                print(f"   Contents: {files}")
                
                # Test if we can write
                test_file = os.path.join(expanded_path, "python_test.txt")
                try:
                    with open(test_file, 'w') as f:
                        f.write("Python can write here")
                    print(f"   ✅ Python can WRITE to this directory")
                    os.remove(test_file)
                except Exception as e:
                    print(f"   ❌ Python cannot write: {e}")
                    
            except Exception as e:
                print(f"   ❌ Cannot list directory: {e}")
    
    # Also check what MT5 might see as Z: drive (common Wine mapping)
    z_drive_path = os.path.expanduser("~/.wine/dosdevices/z:")
    if os.path.exists(z_drive_path):
        print(f"\n🔍 Z: drive mapping exists: {z_drive_path}")
        # This is usually mapped to the macOS root /

if __name__ == "__main__":
    find_wine_mt5_paths()