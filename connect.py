import os
import sys
import asyncio
import time
import re

# --- PATH SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
deps_path = os.path.join(script_dir, "deps")
if deps_path not in sys.path:
    sys.path.insert(0, deps_path)

from bleak import BleakClient, BleakScanner
from dicts import CHARACTERISTICS, COMMANDS, AUDIO_GROUPS

def build_audio_packet(audio_cmd, parameter):
    """Combines AUDIO_BASE with the specific command and parameter."""
    return bytearray(COMMANDS["AUDIO_BASE"] + [audio_cmd, parameter])

def print_menu(current_group, mac, display_name):
    """Clears screen and prints the dynamic status header."""
    os.system('clear' if os.name == 'posix' else 'cls')
    # Dynamic header based on scanned personality
    print(f"--- {display_name.upper()} ---")
    print(f"--- ADDR: {mac} | LAST GROUP: {current_group} ---\n")
    
    for g_id, g_name in AUDIO_GROUPS.items():
        print(f"{g_id}: {g_name}")
    
    print("\n[Q] Quit | [SCAN] Catalog All | [G#C#] Play Specific")
    print("-" * 65)

async def auth_sequence(mac: str, display_name: str):
    cmd_uuid = CHARACTERISTICS["COMMAND"]["uuid"]
    current_group = 0

    print(f"[*] Connecting to {display_name}...")
    device = await BleakScanner.find_device_by_address(mac, timeout=5.0)
    if not device: raise Exception("Droid not found.")

    async with BleakClient(device, timeout=10.0) as client:
        # Handshake
        for _ in range(5):
            await client.write_gatt_char(cmd_uuid, bytearray(COMMANDS["LOGON"]), response=False)
            await asyncio.sleep(0.1)
        
        await client.write_gatt_char(cmd_uuid, bytearray(COMMANDS["PAIR_A"]), response=False)
        await client.write_gatt_char(cmd_uuid, build_audio_packet(0x18, 0x02), response=False)

        while True:
            if not client.is_connected:
                print("\n[!] Connection lost.")
                break

            print_menu(current_group, mac, display_name)
            
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(None, input, "Droid Command > ")
                user_input = user_input.upper().strip()
            except EOFError: break
            
            if user_input == 'Q': break

            if user_input == 'SCAN':
                for g in range(0, 12):
                    print(f"\n[*] SWITCHING TO GROUP {g}...")
                    await client.write_gatt_char(cmd_uuid, build_audio_packet(0x1f, g), False)
                    current_group = g
                    await asyncio.sleep(0.3)

                    for c in range(0, 15):
                        if not client.is_connected: return
                        print(f"[*] Testing G{g} C{c}...")
                        await client.write_gatt_char(cmd_uuid, build_audio_packet(0x18, c), False)
                        
                        ans = await asyncio.get_event_loop().run_in_executor(None, input, "  Next? (y/n/stop): ")
                        ans = ans.lower().strip()
                        if ans == 'n': break
                        elif ans == 'stop': 
                            user_input = 'STOPPED' 
                            break
                    if user_input == 'STOPPED': break
                continue

            try:
                match = re.match(r"G(\d+)C(\d+)", user_input)
                if match:
                    g_val, c_val = map(int, match.groups())
                    await client.write_gatt_char(cmd_uuid, build_audio_packet(0x1f, g_val), False)
                    current_group = g_val
                    await asyncio.sleep(0.2)
                    await client.write_gatt_char(cmd_uuid, build_audio_packet(0x18, c_val), False)
                else:
                    if user_input != '':
                        print("[!] Format: G#C# (Example: G0C2)")
                        await asyncio.sleep(1.2)
            except Exception as e:
                print(f"[!] Error: {e}")
                await asyncio.sleep(1)

def connection_menu(droid, target_mac, name=None):
    # If name wasn't passed, use a generic label
    display_name = name if name else "Unknown Droid"
    try:
        asyncio.run(auth_sequence(target_mac, display_name))
    except Exception as e:
        print(f"\n[!] Session Ended: {e}")
        time.sleep(2)