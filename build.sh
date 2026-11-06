#!/bin/bash
# Build script for Gorillas standalone executable
# Supports Linux, macOS, and BSD (FreeBSD, OpenBSD, NetBSD)

set -e

echo "=== Gorillas Game Build Script ==="
echo ""

# Detect platform
OS_TYPE="$(uname -s)"
case "${OS_TYPE}" in
    Linux*)     PLATFORM=linux;;
    Darwin*)    PLATFORM=macos;;
    FreeBSD*)   PLATFORM=freebsd;;
    OpenBSD*)   PLATFORM=openbsd;;
    NetBSD*)    PLATFORM=netbsd;;
    *)          PLATFORM=unknown;;
esac

echo "Detected platform: ${PLATFORM} (${OS_TYPE})"
echo ""

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Error: Python not found. Please install Python 3.10+"
    exit 1
fi

echo "Using Python: $($PYTHON --version)"
echo ""

# Platform-specific setup
case "${PLATFORM}" in
    linux)
        echo "Linux build detected."
        echo "Make sure you have SDL2 development libraries installed."
        echo "  Debian/Ubuntu: sudo apt install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev"
        echo "  Fedora: sudo dnf install SDL2-devel SDL2_image-devel SDL2_mixer-devel SDL2_ttf-devel"
        echo "  Arch: sudo pacman -S sdl2 sdl2_image sdl2_mixer sdl2_ttf"
        echo ""
        ;;
    macos)
        echo "macOS build detected."
        echo "Make sure you have Homebrew and SDL2 installed:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "  brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi"
        echo ""
        ;;
    freebsd|openbsd|netbsd)
        echo "${PLATFORM} build detected."
        echo "Make sure you have SDL2 installed:"
        echo "  pkg install sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi"
        echo ""
        ;;
esac

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv .venv
fi

# Activate venv
echo "Activating virtual environment..."
source .venv/bin/activate

# Install pinned dependencies
echo "Installing pinned dependencies from requirements.txt..."
pip install -r requirements.txt

# Check if PyInstaller is installed (pinned for reproducible builds)
PYINSTALLER_VERSION="pyinstaller==6.22.3"
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip install "$PYINSTALLER_VERSION"
fi

echo ""
echo "Building standalone executable..."

# Clean previous builds
rm -rf build dist

# Build with PyInstaller
pyinstaller gorillas.spec

# Determine output name based on platform
OUTPUT_NAME="gorillas"
case "${PLATFORM}" in
    macos) OUTPUT_NAME="gorillas-macos";;
    freebsd) OUTPUT_NAME="gorillas-freebsd";;
    openbsd) OUTPUT_NAME="gorillas-openbsd";;
    netbsd) OUTPUT_NAME="gorillas-netbsd";;
    linux) OUTPUT_NAME="gorillas-linux";;
esac

# Rename the executable
if [ -f "dist/gorillas" ]; then
    mv "dist/gorillas" "dist/${OUTPUT_NAME}"
    echo ""
    echo "=== Build Complete! ==="
    echo ""
    echo "Executable location: dist/${OUTPUT_NAME}"
    echo ""
    echo "To test it:"
    echo "  ./dist/${OUTPUT_NAME}"
    echo ""
    echo "To test with CGA mode:"
    echo "  ./dist/${OUTPUT_NAME} --cga"
    echo ""
    echo "To test with scaling:"
    echo "  ./dist/${OUTPUT_NAME} --scale 2"
    echo ""
    echo "File size:"
    ls -lh "dist/${OUTPUT_NAME}"
else
    echo ""
    echo "Error: Build failed. Check the output above for errors."
    exit 1
fi
