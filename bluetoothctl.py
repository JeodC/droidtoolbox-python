import queue
import subprocess
import threading
import time

class BluetoothCtl:
    def __init__(self):
        self.proc = subprocess.Popen(
            ["bluetoothctl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._reader_thread = threading.Thread(target=self._reader, daemon=True)
        self._reader_thread.start()
        
        self.power_on()

    def _reader(self):
        """Thread to capture bluetoothctl output"""
        try:
            while not self._stop_event.is_set():
                line = self.proc.stdout.readline()
                if not line: break
                self._queue.put(line)
        except Exception:
            pass

    def _send(self, cmd: str, delay: float = 0.1):
        """Pipe writer"""
        if self.proc.poll() is not None: return
        try:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()
            time.sleep(delay)
        except (BrokenPipeError, OSError):
            pass

    def _drain_output(self) -> list[str]:
        """Buffer clearer"""
        lines = []
        while not self._queue.empty():
            try:
                lines.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return lines

    def power_on(self):
        """Ensures the Bluetooth hardware is active."""
        self._send("power on")

    def start_scanning(self):
        """Tells the hardware to look for new devices"""
        self._send("scan on")

    def stop_scanning(self):
        """Tells the hardware to stop looking"""
        self._send("scan off")

    def get_info(self, mac: str) -> str:
        """Fetch device metadata"""
        self._drain_output()
        self._send(f"info {mac}")
        time.sleep(0.8)
        lines = self._drain_output()
        return "\n".join(lines)

    def broadcast_mfg(self, mfg_id: str, mfg_data: str):
        """Configures and starts BLE advertising"""
        self._send("advertise off")
        self._send("menu advertise")
        self._send("clear")
        self._send(f"manufacturer {mfg_id} {mfg_data}")
        self._send("name on")
        self._send("back")
        self._send("advertise on")

    def stop_advertising(self):
        """Stops the current BLE broadcast"""
        self._send("advertise off")

    def close(self):
        """Graceful shutdown of the subprocess"""
        self._stop_event.set()
        self.stop_advertising()
        self._send("quit")
        try:
            self.proc.wait(timeout=1.5)
        except:
            self.proc.kill()