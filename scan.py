import os
import re
import subprocess
import time

from dicts import FACTIONS, DROIDS

class DroidScanner:
    def __init__(self, bt_controller):
        self.bt = bt_controller
        self.base_dir = os.path.dirname(os.path.realpath(__file__))
        self._namefile = os.path.join(self.base_dir, ".names")

    def _get_raw_devices(self):
        """Directly queries the OS for visible Bluetooth devices"""
        return subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True).stdout

    def _parse_personality(self, info_text):
        """Uses regex to extract and decode personality hex from manufacturer data"""
        if "ManufacturerData.Value" not in info_text:
            return None
        try:
            parts = info_text.split("ManufacturerData.Value:")[1].split("AdvertisingFlags:")[0]
            clean_hex = "".join(re.findall(r'[0-9a-fA-F]+', parts)).lower()

            if "0304" in clean_hex:
                start = clean_hex.find("0304")
                payload = clean_hex[start:start+12]
                if len(payload) == 12:
                    raw_aff_byte = int(payload[8:10], 16)
                    raw_pers_val = int(payload[10:12], 16)
                    derived_aff_id = (raw_aff_byte - 0x80) // 2

                    # Match against dicts.py
                    for f_label, droids_dict in DROIDS.items():
                        if FACTIONS.get(f_label) == derived_aff_id:
                            for d_info in droids_dict.values():
                                if d_info["id"] == raw_pers_val:
                                    return f"{f_label} | {d_info['name']}"
                    return f"Unknown Faction ({derived_aff_id}) | Unknown ID ({raw_pers_val})"
        except:
            return "Parse Error"
        return None

    def _load_names(self):
        """Reads the .names file into a dict"""
        names = {}
        if os.path.exists(self._namefile):
            with open(self._namefile, "r") as f:
                for line in f:
                    if "|" in line:
                        mac, name = line.strip().split("|", 1)
                        names[mac.upper()] = name
        return names
        
    def _save_all_names(self, name_dict):
        """Syncs the FAVORITES dict with the .names file"""
        with open(self._namefile, "w") as f:
            for m, n in name_dict.items():
                f.write(f"{m}|{n}\n")

    def scan_for_droids(self):
        """Returns a list of MAC addresses identified as 'DROID'"""
        raw_output = self._get_raw_devices()
        return [l.split()[1] for l in raw_output.splitlines() if "DROID" in l.upper()]

    def get_droid_identity(self, mac):
        """Returns the Faction and Personality name for a given MAC"""
        info_text = self.bt.get_info(mac)
        return self._parse_personality(info_text)

    def get_saved_name(self, mac):
        """Returns the user-defined name for a MAC if it exists"""
        names = self._load_names()
        return names.get(mac.upper())

    def save_custom_name(self, mac, name):
        """Saves/Updates a custom name for a MAC"""
        names = self._load_names()
        names[mac.upper()] = name
        self._save_all_names(names)
                
    def delete_saved_name(self, mac):
        """Removes a droid from the saved names file"""
        names = self._load_names()
        mac_upper = mac.upper()
        
        if mac_upper in names:
            del names[mac_upper]
            self._save_all_names(names) 
            return True
        return False