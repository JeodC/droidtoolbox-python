import os
import subprocess
import time
import re

from connect import connection_menu
from dicts import FACTIONS, DROIDS

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
NAMEFILE = os.path.join(BASE_DIR, ".names")

def decode_droid_packet(info_text):
    if "ManufacturerData.Value" not in info_text:
        return None

    try:
        # Isolate and clean hex from multi-line output
        parts = info_text.split("ManufacturerData.Value:")[1].split("AdvertisingFlags:")[0]
        clean_hex = "".join(re.findall(r'[0-9a-fA-F]+', parts)).lower()

        if "0304" in clean_hex:
            start = clean_hex.find("0304")
            payload = clean_hex[start:start+12]

            if len(payload) == 12:
                raw_aff_byte = int(payload[8:10], 16)
                raw_pers_val = int(payload[10:12], 16)
                derived_aff_id = (raw_aff_byte - 0x80) // 2

                chip_name = f"Unknown Personality (0x{raw_pers_val:02X})"
                faction_label = f"Unknown Faction ({derived_aff_id})"

                for f_label, droids_dict in DROIDS.items():
                    if FACTIONS.get(f_label) == derived_aff_id:
                        faction_label = f_label
                        for d_id, d_info in droids_dict.items():
                            if d_info["id"] == raw_pers_val:
                                chip_name = d_info["name"]
                                break
                        break

                return f"{faction_label} | {chip_name}"

    except Exception as e:
        return f"Scan Error: {e}"

    return "Pulse Out of Range"

def scan_for_data(bt, target_mac):
    for attempt in range(6):
        bt.send("scan on")
        time.sleep(1.2)
        bt.send("scan off")
        info_text = bt.get_info(target_mac)
        decoded = decode_droid_packet(info_text)
        if decoded:
            return decoded

        time.sleep(0.4)
    return None

def load_friendly_names():
    names = {}
    if os.path.exists(NAMEFILE):
        with open(NAMEFILE, "r") as f:
            for line in f:
                if "|" in line:
                    mac, name = line.strip().split("|", 1)
                    names[mac.upper()] = name
    return names

def save_friendly_name(mac, name):
    names = load_friendly_names()
    names[mac.upper()] = name
    with open(NAMEFILE, "w") as f:
        for mac_addr, n in names.items():
            f.write(f"{mac_addr}|{n}\n")

def scanning_menu(droid):
    friendly_names = load_friendly_names()

    while True:
        os.system('clear')
        print("--- DROID SCANNER ---")

        print("\nScanning for Droids...\n")
        droid.bt.send("scan on")
        time.sleep(2)
        droid.bt.send("scan off")

        devices = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True).stdout
        found_macs = [l.split()[1] for l in devices.splitlines() if "DROID" in l.upper()]

        session_droids = []

        if not found_macs:
            print("No Droids found. Try 'R' to Rescan.")
        else:
            for index, mac in enumerate(found_macs, 1):
                mac_upper = mac.upper()
                session_droids.append(mac_upper)
                nickname = friendly_names.get(mac_upper)
                data = scan_for_data(droid.bt, mac)
                display_label = nickname if nickname else data
                
                print(f"[{index}] {display_label}")
                print(f"    MAC: {mac_upper}")

        print("-" * 50)
        print("R. Rescan | N# Name | S# Save | C# Connect | Q. Back")

        cmd = input("\nSelect > ").lower().strip()

        if not cmd: continue

        if cmd == 'q':
            break
        elif cmd == 'r':
            continue
        elif cmd.startswith('c'):
            try:
                idx = int(cmd[1:]) - 1
                target_mac = session_droids[idx]
                nickname = friendly_names.get(target_mac)
                pulse_data = scan_for_data(droid.bt, target_mac)
                if nickname:
                    final_name = f"{nickname} ({pulse_data if pulse_data else 'Unknown Chip'})"
                elif pulse_data:
                    final_name = pulse_data
                else:
                    final_name = "Unknown Droid"

                connection_menu(droid, target_mac, final_name)
                
            except (IndexError, ValueError):
                print("!! Invalid format. Use C1, C2, etc.")
                time.sleep(1.5)
        elif cmd.startswith('n'):
            try:
                num_str = cmd[1:]
                idx = int(num_str) - 1
                target_mac = session_droids[idx]

                new_name = input(f"Enter name for {target_mac}: ").strip()
                if new_name:
                    save_friendly_name(target_mac, new_name)
                    friendly_names = load_friendly_names()
            except (IndexError, ValueError):
                print("!! Invalid format. Use N1, N2, etc.")
                time.sleep(1.5)
        elif cmd.startswith('s'):
            try:
                idx = int(cmd[1:]) - 1
                target_mac = session_droids[idx]
                pulse_data = scan_for_data(droid.bt, target_mac)
                
                save_name = pulse_data if pulse_data else "Unknown Droid"
                save_friendly_name(target_mac, save_name)
                
                print(f"[*] Added {target_mac} to Favorites.")
                friendly_names = load_friendly_names()
                time.sleep(1)
            except:
                print("!! Error saving.")
