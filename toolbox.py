import subprocess
import time
import os

class DroidController:
    def __init__(self):
        self.current_active = "None (Idle)"
        self.hw_status = "Unknown"
        self.adapter_info = "N/A"
        self.bt = None
        self.check_capabilities()

        try:
            self.bt = subprocess.Popen(
                ['bluetoothctl'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1
            )
            self._send("power on")
            self._send("menu advertise")
            self._send("clear")
            self._send("name DROID_BEACON")
        except FileNotFoundError:
            self.hw_status = "MISSING (bluetoothctl)"

    def check_capabilities(self):
        try:
            res = subprocess.run(['bluetoothctl', 'show'], capture_output=True, text=True, timeout=2)
            self.hw_status = "READY" if "Powered: yes" in res.stdout else "OFF"
            for line in res.stdout.split('\n'):
                if "Controller" in line:
                    self.adapter_info = line.replace("Controller ", "").strip()
                    break
        except Exception:
            self.hw_status = "ERROR"

    def _send(self, cmd):
        try:
            self.bt.stdin.write(f"{cmd}\n")
            self.bt.stdin.flush()
            time.sleep(0.1)
        except: pass

    def activate_location(self, loc_id, name, cooldown_byte):
        payload = (
            f"0x0183"                      # Manufacturer ID (Disney)
            f"0x0A"                        # Type: Location Beacon
            f"0x04"                        # Data Length
            f"0x{loc_id:02X}"              # Zone ID (1-7)
            f"0x{cooldown_byte:02X}"       # Cooldown
            f"0xA6"                        # RSSI Threshold
            f"0x01"                        # Activation Bit
        )
        self._broadcast(name, payload)

    def activate_droid_trigger(self, p_id, p_name, aff_id):
        aff_map = {0x01: "Scoundrel", 0x05: "Resistance", 0x09: "First Order"}
        aff_label = aff_map.get(aff_id, "Unknown")
        
        aff_byte = 0x80 + (aff_id * 2)
        payload = (
            f"0x0183 "           # Manufacturer ID
            f"0x03 "             # Type: Droid Beacon
            f"0x04 "             # Data Length
            f"0x44 "             # Static Header
            f"0x81 "             # Status (Paired/Active)
            f"0x{aff_byte:02X} " # Affiliation Mask (Scoundrel/Resistance/First Order)
            f"0x{p_id:02X}"   # Personality ID of the 'Ghost' Droid
        )
        
        self._broadcast(f"{aff_label}: {p_name}", payload)

    def _broadcast(self, name, payload):
        self._send("advertise off")
        self._send("clear")
        self._send(f"manufacturer {payload}")
        self._send("back")
        self._send("advertise on")
        self.current_active = name

    def stop(self):
        self._send("advertise off")
        self.current_active = "None (Stopped)"

# Droid signals are extensively documented
# https://docs.google.com/spreadsheets/d/13P_GE6tNYpGvoVUTEQvA3SQzMqpZ-SoiWaTNoJoTV9Q/edit?gid=702279780#gid=702279780

# LOCATION BEACONS
# - Droids that react to a location beacon will not sleep for 6 hours
# - Droids have a minimum cooldown of 1 minute between location beacon reactions
# - Locations mapped: https://galaxysedgetech.epizy.com
LOCATIONS = {
    "1": (0x01, "Market", 0x02),
    "2": (0x02, "Droid Playground", 0x02),
    "3": (0x03, "Resistance Base", 0x02),
    "4": (0x04, "Unknown", 0x02),
    "5": (0x05, "Droid Depot", 0x02),
    "6": (0x06, "Den of Antiquities", 0x02),
    "7": (0x07, "First Order Base", 0x02),
    "8": (0x05, "Oga's Droid Detector", 0xFF),
    "9": (0x07, "First Order Alert", 0xFF)
}

# DROID PERSONALITIES
# - Emulates the presence of another droid
# - Droids will wait 2 minutes between reactions to droid beacons
# - Droids that have reacted to a location beacon within 2 hours will not react to droid beacons
SCOUNDREL = {
    "S1": (0x01, "R-Series (Default)", 0x01),
    "S2": (0x02, "BB-Series (Default)", 0x01),
    "S3": (0x04, "Gray (U9-C4)", 0x01),
    "S4": (0x07, "Purple (M5-BZ)", 0x01),
    "S5": (0x09, "Cyan/Red (CB-23)", 0x01), # CB-23 came with a cyan personality chip, later sold separately as red
    "S6": (0x0D, "Blue (R5-D4)", 0x01),
    "S7": (0x0F, "A-LT Series (Default)", 0x01),
    "S8": (0x10, "White (Drum Kit)", 0x01),
}

RESISTANCE = {
    "R1": (0x03, "Blue (R5-D8)", 0x05),
    "R2": (0x06, "Orange (R4-P17)", 0x05),
    "R3": (0x0A, "Yellow (CH-33P)", 0x05),
    "R4": (0x0B, "C-Series (Default)", 0x05),
    "R5": (0x0C, "D-Unit (Default)", 0x05),
    "R6": (0x0E, "BD-Unit (Default)", 0x05),
    "R7": (0x01, "Green (R2-H15)", 0x05), # Bundled with R2-H15 Holiday Droid, sold in 2025
    "R8": (0x01, "Orange (SPOOK-E)", 0x05) # Bundled with R-Series panels sold in 2025
}

FIRST_ORDER = {
    "F1": (0x05, "Red (0-0-0)", 0x09),
    "F2": (0x08, "Black (BB-9E)", 0x09),
}

ALL_P = {**SCOUNDREL, **RESISTANCE, **FIRST_ORDER}

def draw_interface(droid):
    os.system('clear' if os.name == 'posix' else 'cls')
    C1, C2, C3, C4 = 16, 16, 16, 16
    IW = C1 + C2 + C3 + C4 + 9

    print("┌" + "─"*(IW) + "┐")
    print(f"│{'DROID BEACON CONTROL PANEL':^{IW}}│")
    print("├" + "─"*(IW) + "┤")
    status_line = f" STATUS: {droid.hw_status} | ADAPTER: {droid.adapter_info}"
    print(f"│ {status_line[:IW-2]:<{IW-1}}│")
    
    # Header
    print("├" + "─"*(C1+1) + "┬" + "─"*(C2+2) + "┬" + "─"*(C3+2) + "┬" + "─"*(C4+1) + "┤")
    print(f"│{'LOCATION':^{C1+1}}│{'SCOUNDREL':^{C2+2}}│{'RESISTANCE':^{C3+2}}│{'FIRST ORDER':^{C4+1}}│")
    print("├" + "─"*(C1+1) + "┼" + "─"*(C2+2) + "┼" + "─"*(C3+2) + "┼" + "─"*(C4+1) + "┤")
    
    l_keys = sorted(LOCATIONS.keys())
    s_keys = sorted(SCOUNDREL.keys(), key=lambda x: int(x[1:]))
    r_keys = sorted(RESISTANCE.keys(), key=lambda x: int(x[1:]))
    f_keys = sorted(FIRST_ORDER.keys(), key=lambda x: int(x[1:]))
    
    max_rows = max(len(l_keys), len(s_keys), len(r_keys), len(f_keys))
    
    for i in range(max_rows):
        l = f"{l_keys[i]}. {LOCATIONS[l_keys[i]][1]}" if i < len(l_keys) else ""
        s = f"{s_keys[i]}. {SCOUNDREL[s_keys[i]][1]}" if i < len(s_keys) else ""
        r = f"{r_keys[i]}. {RESISTANCE[r_keys[i]][1]}" if i < len(r_keys) else ""
        f = f"{f_keys[i]}. {FIRST_ORDER[f_keys[i]][1]}" if i < len(f_keys) else ""
        
        print(f"│{l:<{C1}} │ {s:<{C2}} │ {r:<{C3}} │ {f:<{C4}}│")

    print("├" + "─"*(IW) + "┤")
    print(f"│{'S: Stop | Q: Quit | Enter: Refresh':^{IW}}│")
    print("├" + "─"*IW + "┤")

    # Footer
    active_str = f" ACTIVE: {droid.current_active}"
    print(f"│{active_str:<{IW}}│")
    print("└" + "─"*IW + "┘")

def main():
    droid = DroidController()
    while True:
        draw_interface(droid)
        choice = input(" Select ID (e.g., 1, S1, R5) > ").upper()
        if not choice: 
            droid.check_capabilities()
            continue
        if choice in LOCATIONS: droid.activate_location(*LOCATIONS[choice])
        elif choice in ALL_P: droid.activate_droid_trigger(*ALL_P[choice])
        elif choice == 'S': droid.stop()
        elif choice == 'Q': break

if __name__ == "__main__":
    main()
