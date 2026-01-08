import os
import sys
import shutil
import time

# Get the directory where main.py lives
script_dir = os.path.dirname(os.path.abspath(__file__))
# Point to the deps folder next to it
sys.path.append(os.path.join(script_dir, "deps"))
# If you put bleak inside a 'bleak' subfolder in deps, add that too
sys.path.append(os.path.join(script_dir, "deps", "bleak"))

from bluetoothctl import BluetoothCtl
from beacon import DroidController, beacon_menu
from scan import scanning_menu, load_friendly_names, NAMEFILE
from dicts import FAVORITES

def refresh_favorites():
    if not os.path.exists(NAMEFILE):
        return

    FAVORITES.clear()
    
    try:
        with open(NAMEFILE, "r") as f:
            for index, line in enumerate(f, 1):
                if "|" in line:
                    parts = line.strip().split("|", 1)
                    if len(parts) == 2:
                        mac, name = parts
                        FAVORITES[str(index)] = {
                            "name": name,
                            "mac": mac.upper()
                        }
    except Exception as e:
        print(f"Error loading .names: {e}")

def favorites_menu(droid: DroidController):
    while True:
        refresh_favorites()
        
        os.system('clear' if os.name == 'posix' else 'cls')
        print("--- KNOWN DROIDS ---")
        
        if not FAVORITES:
            print("\nNo droids saved yet.")
        else:
            for key, info in FAVORITES.items():
                print(f"[{key}] {info['name']}")
                print(f"    MAC: {info['mac']}")
        
        print("\n[B] Back | [#] Connect | [D#] Delete")
        
        user_input = input("\nSelect > ").strip().upper()
        
        if user_input == 'B':
            break
        
        if not user_input:
            continue

        # --- DELETE LOGIC ---
        if user_input.startswith('D'):
            try:
                idx = user_input[1:]
                if idx in FAVORITES:
                    target = FAVORITES[idx]
                    confirm = input(f"Remove {target['name']}? (y/N): ").lower()
                    
                    if confirm == 'y':
                        # 1. Load the current full list from the file
                        current_list = load_friendly_names()
                        # 2. Remove the specific MAC
                        if target['mac'] in current_list:
                            del current_list[target['mac']]
                        
                        # 3. Rewrite the file
                        with open(NAMEFILE, "w") as f:
                            for mac_addr, name in current_list.items():
                                f.write(f"{mac_addr}|{name}\n")
                        
                        print(f"[*] {target['name']} removed.")
                        time.sleep(1)
                else:
                    print("!! Invalid Selection.")
                    time.sleep(1)
            except Exception as e:
                print(f"!! Error deleting: {e}")
                time.sleep(1.5)

        # --- CONNECT LOGIC ---
        elif user_input in FAVORITES:
            target = FAVORITES[user_input]
            os.system(f"bluetoothctl remove {target['mac']} > /dev/null 2>&1")
            
            from connect import connection_menu
            connection_menu(droid, target['mac'], target['name'])

def main_menu(droid: DroidController):
    # Hardcoded details for Direct Connect
    TARGET_MAC = "D6:25:57:7D:EC:1D"
    TARGET_NAME = "My Droid (Direct)"

    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print(f"{'--- DROID TOOLBOX MAIN MENU ---'}")
        print("\n1. Droid Scan")
        print("2. Emit Beacon")
        print("3. Connect")
        print("Q. Quit")
        
        choice = input("\nSelect > ").upper()
        
        if choice == '1':
            from scan import scanning_menu
            scanning_menu(droid)
        elif choice == '2':
            beacon_menu(droid)
        elif choice == '3':
            favorites_menu(droid)
        elif choice == 'Q':
            break

def main():
    # Check for bluetoothctl
    if shutil.which("bluetoothctl") is None:
        print("ERROR: bluetoothctl not found. This program requires Linux with BlueZ.")
        input("Press any key to quit...")
        return

    # Try to initialize BluetoothCtl
    try:
        bt = BluetoothCtl()
    except FileNotFoundError:
        print("ERROR: Failed to initialize BluetoothCtl.")
        input("Press any key to quit...")
        return

    droid = DroidController(bt)
    try:
        main_menu(droid)
    finally:
        droid.shutdown()

if __name__ == "__main__":
    main()
