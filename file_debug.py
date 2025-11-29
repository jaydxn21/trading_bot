# file_debug.py
import os
import stat
import json
from pathlib import Path

def debug_file_system():
    signal_file = "/tmp/QuantumTrader/signals.json"
    directory = "/tmp/QuantumTrader"
    
    print("=== FILE SYSTEM DEBUG ===")
    print(f"Signal file: {signal_file}")
    print(f"Directory: {directory}")
    
    # Check directory
    print(f"\n📁 Directory exists: {os.path.exists(directory)}")
    if os.path.exists(directory):
        dir_stat = os.stat(directory)
        print(f"Directory permissions: {oct(dir_stat.st_mode)}")
        print(f"Directory owner: {dir_stat.st_uid}")
    
    # Check file
    print(f"\n📄 File exists: {os.path.exists(signal_file)}")
    if os.path.exists(signal_file):
        file_stat = os.stat(signal_file)
        print(f"File permissions: {oct(file_stat.st_mode)}")
        print(f"File owner: {file_stat.st_uid}")
        print(f"File size: {file_stat.st_size} bytes")
        
        # Try to read file
        try:
            with open(signal_file, 'r') as f:
                content = json.load(f)
            print("✅ Can read file content:")
            print(json.dumps(content, indent=2))
        except Exception as e:
            print(f"❌ Cannot read file: {e}")
    
    # List files in /tmp
    print(f"\n📂 Files in /tmp/ (filtered):")
    try:
        tmp_files = os.listdir('/tmp')
        quantum_files = [f for f in tmp_files if 'Quantum' in f or 'quantum' in f]
        for f in quantum_files:
            full_path = f"/tmp/{f}"
            if os.path.isdir(full_path):
                print(f"  📁 {f}/")
                try:
                    sub_files = os.listdir(full_path)
                    for sf in sub_files:
                        print(f"    📄 {sf}")
                except:
                    print(f"    ❌ Cannot list directory contents")
            else:
                print(f"  📄 {f}")
    except Exception as e:
        print(f"❌ Cannot list /tmp directory: {e}")

if __name__ == "__main__":
    debug_file_system()