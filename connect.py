import asyncio
import os
import re
import sys
import time

# --- PATH SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(script_dir, "deps"))

from bleak import BleakClient, BleakScanner
from dicts import CHARACTERISTICS, COMMANDS, AUDIO_GROUPS

class DroidConnection:
    def __init__(self, bt_controller):
        self.bt = bt_controller
        self.client = None
        self._cmd_uuid = CHARACTERISTICS["COMMAND"]["uuid"]
        
    @property
    def is_connected(self):
        """Status check for the UI"""
        return self.client is not None and self.client.is_connected

    async def _write(self, data: bytearray) -> bool:
        """Low-level GATT write with safety checks"""
        if not self.is_connected:
            return False
        try:
            await self.client.write_gatt_char(self._cmd_uuid, data, response=False)
            return True
        except Exception:
            return False

    async def connect(self, mac: str) -> bool:
        """Connects and performs the mandatory LOGON handshake"""
        device = await BleakScanner.find_device_by_address(mac, timeout=5.0)
        if not device:
            return False

        self.client = BleakClient(device, timeout=10.0)
        try:
            await self.client.connect()
            
            # Auth handshake: Needs a few repetitions to guarantee pickup
            for _ in range(3):
                await self._write(bytearray(COMMANDS["LOGON"]))
                await asyncio.sleep(0.1)
            
            # Success sound (Group 0, Clip 2)
            await self.send_audio(0, 0x02)
            return True
        except Exception:
            self.client = None
            return False

    async def send_audio(self, group: int, clip: int) -> bool:
        """Triggers a droid audio clip"""
        base = COMMANDS["AUDIO_BASE"]
        # Set Audio Group
        if await self._write(bytearray(base + [0x1f, group])):
            await asyncio.sleep(0.1)
            # Play Specific Clip
            return await self._write(bytearray(base + [0x18, clip]))
        return False

    async def run_script(self, script_id: int) -> bool:
        """Executes a pre-defined droid animation script"""
        # Block script 19 as it keeps the motors on
        if script_id in [19, 0x13]:
            return False
            
        packet = bytearray([0x25, 0x00, 0x0C, 0x42, script_id, 0x02])
        return await self._write(packet)

    async def disconnect(self):
        """Graceful teardown of the BLE link"""
        if self.is_connected:
            await self.client.disconnect()
        self.client = None