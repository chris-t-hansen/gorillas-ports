#!/bin/bash
# Simplified build script for Gorillas standalone executable
# Assumes Python dependencies are already installed

set -e

echo "=== Gorillas Game Build Script ==="
echo ""

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found. Please run:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo "  pip install pyinstaller"
    exit 1
fi

# Activate venv
source .venv/bin/activate

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

echo "Building standalone executable..."

# Clean previous builds
rm -rf build dist

# Build with PyInstaller
pyinstaller gorillas.spec

echo ""
echo "=== Build Complete! ==="
echo ""
echo "Executable location: dist/gorillas"
echo ""
echo "To test it:"
echo "  ./dist/gorillas"
echo ""
echo "To test with CGA mode:"
echo "  ./dist/gorillas --cga"
echo ""
echo "To test with scaling:"
echo "  ./dist/gorillas --scale 2"
echo ""
echo "File size:"
ls -lh dist/gorillas
