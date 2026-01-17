#!/bin/bash
set -e

# Minimum Python version required
PYTHON_MIN=3.11

# Check Python version
PYTHON_BIN=$(which python3 || true)
if [ -z "$PYTHON_BIN" ]; then
    echo "Python3 not found. Please install Python $PYTHON_MIN or higher."
    exit 1
fi

PYTHON_VER=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$($PYTHON_BIN -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_BIN -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    echo "Python version $PYTHON_VER detected. Please use Python $PYTHON_MIN or higher."
    exit 1
fi

echo "Using Python $PYTHON_VER at $PYTHON_BIN"

# Reset local changes
echo "Resetting local changes to origin/main..."
git fetch
git reset --hard origin/main

# Install Python dependencies (including PyInstaller)
if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies..."
    $PYTHON_BIN -m pip install --upgrade pip
    $PYTHON_BIN -m pip install -r requirements.txt
fi

# Ensure PyInstaller is installed
$PYTHON_BIN -m pip install --upgrade pyinstaller

# Move into app folder
cd app

# Build with PyInstaller into ../dist
pyinstaller \
    --onefile \
    --clean \
    --name SWGE_DroidToolbox \
    --collect-all sdl2 \
    --collect-all bleak \
    --collect-all dbus_fast \
    --add-data "res:res" \
    --distpath ../dist \
    main.py

# Return to root folder
cd ..

echo "Build complete. Output is in ./dist/SWGE_DroidToolbox"
