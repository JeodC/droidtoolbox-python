#!/usr/bin/env python3
"""
main.py - Entrypoint for Droid Toolbox
"""

import glob
import os
import sys

# Add dependencies to path
if hasattr(sys, "_MEIPASS"):
    # Use this for PyInstaller
    BASE_PATH = sys._MEIPASS
else:
    # Use local path for dev
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# Only add local dependencies in dev mode
DEPS_PATH = os.path.join(BASE_PATH, "deps")
if not hasattr(sys, "_MEIPASS") and os.path.isdir(DEPS_PATH):
    sys.path.insert(0, DEPS_PATH)

import sdl2

# Global log file descriptor
_log_fd = None

# ----------------------------------------------------------------------
# Logging setup
# ----------------------------------------------------------------------
def initialize_logging() -> None:
    global _log_fd
    log_dir = os.path.join(BASE_PATH, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Delete oldest logs if more than 3 exist
    log_files = sorted(glob.glob(os.path.join(log_dir, "*.txt")), key=os.path.getmtime)
    while len(log_files) >= 3:
        os.remove(log_files[0])
        log_files.pop(0)

    log_file = os.environ.get("LOG_FILE", os.path.join(log_dir, "log.txt"))
    try:
        _log_fd = open(log_file, "w", buffering=1)
        sys.stdout = sys.stderr = _log_fd
    except Exception as e:
        print(f"Failed to open log file {log_file}: {e}", file=sys.__stdout__)
        _log_fd = sys.__stdout__

# ----------------------------------------------------------------------
# Cleanup helper
# ----------------------------------------------------------------------
def cleanup(toolbox, exit_code: int) -> None:
    if toolbox:
        try:
            toolbox.cleanup()
        except Exception as e:
            print(f"Toolbox cleanup error: {e}", file=sys.__stdout__)

    if _log_fd and not getattr(_log_fd, "closed", True):
        try:
            _log_fd.flush()
            _log_fd.close()
        except Exception:
            pass

    sdl2.SDL_Quit()
    sys.exit(exit_code)

# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------
def main() -> None:
    from toolbox import DroidToolbox

    initialize_logging()
    
    # Log environment context
    mode = "Frozen (PyInstaller)" if hasattr(sys, "_MEIPASS") else "Source/Dev"
    print(f"--- Droid Toolbox Starting ---")
    print(f"Mode: {mode}")
    print(f"Base Path: {BASE_PATH}")
    print(f"Python Version: {sys.version}")

    # SDL initialization
    if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_GAMECONTROLLER) < 0:
        print(f"SDL2 init failed: {sdl2.SDL_GetError()}")
        sys.exit(1)
        
    toolbox = None
    try:
        toolbox = DroidToolbox()
        toolbox.start()

        while toolbox.running:
            toolbox.ui.draw_start()
            toolbox.update()
            toolbox.ui.render_to_screen()
            toolbox.input.clear_ui_states()
            sdl2.SDL_Delay(16)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        cleanup(toolbox, 0)
    except Exception as e:
        import traceback
        print("--- CRASH REPORT ---")
        traceback.print_exc()
        cleanup(toolbox, 1)
    else:
        print("Exiting Droid Toolbox...")
        cleanup(toolbox, 0)
    finally:
        if toolbox is None and sdl2.SDL_WasInit(0):
            sdl2.SDL_Quit()


if __name__ == "__main__":
    main()
