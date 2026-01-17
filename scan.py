#!/usr/bin/env python3
"""
scan.py - Performs the logic in scan actions
"""

import os
import re
import subprocess
import time
import threading

from dicts import FACTIONS, DROIDS

# ----------------------------------------------------------------------
# DroidScanner (Low Level)
# ----------------------------------------------------------------------
class DroidScanner:
    def __init__(self, bt_controller):
        self.bt = bt_controller

    def _parse_personality(self, info_text):
        """Parses hex code to determine the personality and faction of a droid"""
        if not info_text or "ManufacturerData" not in info_text:
            return None
        try:
            if "ManufacturerData.Value" in info_text:
                parts = info_text.split("ManufacturerData.Value:")[1]
            else:
                parts = info_text.split("ManufacturerData Value:")[1]

            parts = re.split(r'AdvertisingFlags|RSSI|TxPower|ServiceData', parts)[0]
            clean_hex = "".join(re.findall(r'[0-9a-fA-F]+', parts)).lower()

            if "0304" in clean_hex:
                start = clean_hex.find("0304")
                payload = clean_hex[start:start+12]

                if len(payload) >= 12:
                    raw_aff_byte = int(payload[8:10], 16)
                    raw_pers_val = int(payload[10:12], 16)
                    derived_aff_id = (raw_aff_byte - 0x80) // 2
                    
                    target_f_key = None
                    for f_key, f_val in FACTIONS.items():
                        if f_val == derived_aff_id:
                            target_f_key = f_key
                            break

                    if target_f_key:
                        faction_droids = DROIDS.get(target_f_key, {})
                        for d_info in faction_droids.values():
                            if d_info["id"] == raw_pers_val:
                                return f"{d_info['name']} ({target_f_key})"
                        return f"Unknown ID:{hex(raw_pers_val)} ({target_f_key})"
            return None
        except Exception:
            return None

# ----------------------------------------------------------------------
# Scan Manager (High Level)
# ----------------------------------------------------------------------
class ScanManager:
    def __init__(self, bt_controller, lock=None, favorites=None, progress_callback=None):
        self.bt = bt_controller
        self.scanner = DroidScanner(bt_controller)
        self._lock = lock or threading.Lock()
        self.favorites = favorites or {}
        self.scanning = False
        self.scan_results = []
        self.progress_callback = progress_callback

    def start_scan(self, duration=3.0):
        """Initiates the background thread to perform a non-blocking device scan"""
        if self.scanning:
            return
        self.scanning = True
        threading.Thread(target=self._scan_thread, args=(duration,), daemon=True).start()

    def stop_scan(self):
        """Signals the Bluetooth controller to cease discovery and updates state"""
        self.scanning = False

    def _scan_thread(self, duration):
        try:
            self.bt.power_on()
            
            # Broad discovery to populate the device list
            subprocess.run(["bluetoothctl", "scan", "on"], timeout=duration, capture_output=True)
            
            # Get the list of all MACs the OS currently sees
            raw_devs = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True).stdout
            found_macs = [l.split()[1] for l in raw_devs.splitlines() if "DROID" in l.upper()]
            
            # Get current favorites to check for existing profiles
            current_favorites = self.favorites or {}
            
            temp_results = []
            for mac in found_macs:
                mac = mac.upper()
                
                # Targeted nudge to refresh attributes
                subprocess.run(["bluetoothctl", "scan", "on"], timeout=1.5, capture_output=True)
                
                info_text = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
                identity = self.scanner._parse_personality(info_text)
                
                # --- Profile Hinting Logic ---
                fav_entry = current_favorites.get(mac)
                nickname = None
                profile = "R-Arcade"

                if fav_entry:
                    nickname = fav_entry.get("nickname")
                    profile = fav_entry.get("controller_profile", "R-Arcade")
                else:
                    # New droid found: Hint profile based on identity string
                    if identity:
                        if "BB-Series" in identity:
                            profile = "BB-Arcade"
                
                temp_results.append({
                    "mac": mac,
                    "nickname": nickname,
                    "identity": identity if identity else "Droid Found",
                    "controller_profile": profile
                })

            with self._lock:
                self.scan_results = temp_results

        except Exception as e:
            print(f"Scan Error: {e}")
        finally:
            self.scanning = False

    def get_results(self):
        """Provides a thread-safe copy of the currently discovered droid list"""
        with self._lock:
            return self.scan_results.copy()

    def clear_results(self):
        """Resets the result list and error tracking for a new scan session"""
        with self._lock:
            self.scan_results = []