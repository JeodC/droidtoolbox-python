import os
import time
import asyncio
import re

from scan import DroidScanner
from beacon import DroidBeacon
from connect import DroidConnection
from dicts import FAVORITES, LOCATIONS, DROIDS, AUDIO_GROUPS, UI_STRINGS

class DroidUI:
    def __init__(self, bt_controller):
        self.bt = bt_controller 
        self.scanner = DroidScanner(bt_controller)
        self.beacon = DroidBeacon(bt_controller)
        self.connection = DroidConnection(bt_controller)

    def clear(self):
        os.system('clear' if os.name == 'posix' else 'cls')

    def _draw_beacon_header(self):
        """Renders the consistent beacon status top-bar"""
        self.clear()
        print(UI_STRINGS["BEACON_HEADER_MAIN"])
        print(UI_STRINGS["BEACON_STATUS"].format(status=self.beacon.current_active))

    def _display_list(self, items):
        """Generic list renderer for scannable/saved droids"""
        for index, item in enumerate(items, 1):
            print(UI_STRINGS["LIST_ITEM"].format(
                idx=index, 
                label=item['label'], 
                mac=item['mac']
            ))

    def scanning_menu(self):
        """Live scanning for BLE droids"""
        while True:
            self.clear()
            print(UI_STRINGS["SCAN_HEADER"])
            print(UI_STRINGS["SCAN_MSG"])
            
            # Adjust to control how long to scan
            self.bt.power_on()
            self.bt.start_scanning()
            time.sleep(2)
            self.bt.stop_scanning()

            found_macs = self.scanner.scan_for_droids()
            session_droids = []

            if not found_macs:
                print(UI_STRINGS["SCAN_NONE"])
            else:
                for idx, mac in enumerate(found_macs, 1):
                    mac_upper = mac.upper()
                    session_droids.append(mac_upper)
                    nickname = self.scanner.get_saved_name(mac_upper)
                    data = self.scanner.get_droid_identity(mac_upper)
                    display_label = nickname or data or UI_STRINGS["UNKNOWN"]
                    print(UI_STRINGS["LIST_ITEM"].format(idx=idx, label=display_label, mac=mac_upper))

            print(UI_STRINGS["SCAN_FOOTER"])
            cmd = input(UI_STRINGS["PROMPT"]).strip().upper()
            if not cmd or cmd == 'Q':
                break
            if cmd == 'R':
                continue

            # Parse user input: <action><index>
            try:
                action = cmd[0]
                idx = int(cmd[1:]) - 1
                target_mac = session_droids[idx]
            except (ValueError, IndexError):
                print(UI_STRINGS["INVALID"])
                time.sleep(1)
                continue

            if action == 'C':
                identity = self.scanner.get_droid_identity(target_mac)
                nickname = self.scanner.get_saved_name(target_mac)
                final_name = nickname or identity or UI_STRINGS["UNKNOWN"]
                self.connection_session(target_mac, final_name)

            elif action == 'N':
                new_name = input(UI_STRINGS["NICKNAME"].format(target_mac=target_mac)).strip()
                if new_name:
                    self.scanner.save_custom_name(target_mac, new_name)

    def favorites_menu(self):
        """Manage and connect to saved droids"""
        while True:
            self.clear()
            saved_names = self.scanner._load_names()
            FAVORITES.clear()
            
            print(UI_STRINGS["FAVORITES_HEADER"])
            if not saved_names:
                print(UI_STRINGS["FAVORITES_EMPTY"])
            else:
                for idx, (mac, name) in enumerate(saved_names.items(), 1):
                    FAVORITES[str(idx)] = {"name": name, "mac": mac}
                    print(UI_STRINGS["LIST_ITEM"].format(idx=idx, label=name, mac=mac))

            print(UI_STRINGS["FAVORITES_FOOTER"])
            choice = input(UI_STRINGS["PROMPT"]).strip().upper()
            if choice == 'B':
                break

            if choice.startswith('D'):
                idx = choice[1:]
                if idx in FAVORITES:
                    target = FAVORITES[idx]
                    confirm = input(UI_STRINGS["FAVORITES_DELETE"].format(name=target['name'])).strip().lower()
                    if confirm == 'y':
                        if self.scanner.delete_saved_name(target['mac']):
                            print(UI_STRINGS["FAVORITES_DELCONF"].format(name=target['name']))
                        else:
                            print(UI_STRINGS["FAVORITES_ERROR"])
                        time.sleep(1)
                continue

            if choice in FAVORITES:
                target = FAVORITES[choice]
                os.system(f"bluetoothctl remove {target['mac']} > /dev/null 2>&1")
                self.connection_session(target['mac'], target['name'])

    def beacon_main_menu(self):
        """Main entry point for Bluetooth beaconing"""
        while True:
            self._draw_beacon_header()
            print(UI_STRINGS["BEACON_MAIN_OP1"])
            factions = list(DROIDS.keys())
            for i, faction in enumerate(factions, start=2):
                print(UI_STRINGS["BEACON_MAIN_OP2"].format(index=i, faction=faction))

            print(UI_STRINGS["BEACON_FOOTER_MAIN"])
            choice = input(UI_STRINGS["PROMPT"]).upper().strip()

            if choice == 'Q': break
            if choice == 'S': self.beacon.stop()
            elif choice == '1':
                self._beacon_submenu("LOCATIONS", LOCATIONS, is_location=True)
            elif choice.isdigit():
                idx = int(choice) - 2
                if 0 <= idx < len(factions):
                    faction = factions[idx]
                    self._beacon_submenu(faction, DROIDS[faction])

    def _beacon_submenu(self, title, data_dict, is_location=False):
        """Renders sub-categories for beacons"""
        while True:
            self._draw_beacon_header()
            print(f"\n[{title}]\n")
            
            for key, val in sorted(data_dict.items()):
                display_name = val[1] if is_location else val['name']
                print(f" {key}. {display_name}")

            print(UI_STRINGS["BEACON_FOOTER_SUB"])
            choice = input(UI_STRINGS["PROMPT"]).strip().upper()

            if choice == 'B': break
            if choice == 'S': self.beacon.stop()
            
            elif choice.isdigit() and int(choice) in data_dict:
                selected = data_dict[int(choice)]
                if is_location:
                    self.beacon.activate_location(selected[0], selected[1], selected[2])
                else:
                    self.beacon.activate_droid(selected['id'], selected['name'], title)

    def connection_session(self, mac, name):
        """Active BLE connection loop"""
        loop = asyncio.get_event_loop()
        print(UI_STRINGS["CONN_CONNECTING"].format(name=name))
        
        if not loop.run_until_complete(self.connection.connect(mac)):
            print(UI_STRINGS["CONN_FAILED"])
            time.sleep(2)
            return

        while True:
            if not self.connection.is_connected:
                print(UI_STRINGS["CONN_LOST"])
                time.sleep(2)
                break

            self.clear()
            print(UI_STRINGS["CONN_HEADER_ACTIVE"].format(name=name.upper()))
            print(UI_STRINGS["CONN_STATUS_BAR"].format(mac=mac))
            print(UI_STRINGS["CONN_MAIN_MENU"])
            
            cmd = input(UI_STRINGS["PROMPT"]).upper().strip()
            if cmd == 'Q':
                loop.run_until_complete(self.connection.disconnect())
                break
            elif cmd == 'A':
                self._audio_ui_loop(loop)
            elif cmd == 'S':
                self._script_ui_loop(loop)

    def _audio_ui_loop(self, loop):
        """Interactive audio trigger menu"""
        while True:
            self.clear()
            print(UI_STRINGS["AUDIO_HEADER"])
            for g_id, g_name in AUDIO_GROUPS.items():
                print(f"{g_id}: {g_name}")
            
            choice = input(UI_STRINGS["AUDIO_FOOTER"]).upper().strip()
            if choice == 'B': break
            match = re.match(r"G(\d+)C(\d+)", choice)
            if match:
                g, c = map(int, match.groups())
                loop.run_until_complete(self.connection.send_audio(g, c))

    def _script_ui_loop(self, loop):
        """Interactive animation trigger menu"""
        while True:
            self.clear()
            print(UI_STRINGS["SCRIPT_HEADER"])
            print(UI_STRINGS["SCRIPT_LIST"])
            print(UI_STRINGS["SCRIPT_FOOTER"])
            
            choice = input(UI_STRINGS["PROMPT"]).upper().strip()
            if choice == 'B': break
            if choice.isdigit():
                loop.run_until_complete(self.connection.run_script(int(choice)))
                print(UI_STRINGS["SCRIPT_EXEC"].format(id=choice))
                time.sleep(1)
