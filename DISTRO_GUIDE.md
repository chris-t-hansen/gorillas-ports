# Cross-Distribution Compatibility Guide

This guide explains how to build and distribute the Gorillas game executable across different Linux distributions.

## Understanding Compatibility

The PyInstaller executable bundles Python and most dependencies, but still relies on system libraries:
- **SDL2** (Simple DirectMedia Layer) for graphics and sound
- **glibc** (GNU C Library) for system calls

### Key Compatibility Rules

1. **Build on the oldest target system**: Executables built on newer systems may not work on older ones due to glibc version requirements
2. **Same architecture required**: An executable built on x86_64 won't run on ARM (aarch64), and vice versa
3. **SDL2 runtime libraries**: Users need SDL2 libraries installed on their system

## Distribution-Specific Instructions

### For the Distributor (Building the Executable)

#### Debian/Ubuntu (Recommended for broad compatibility)
```bash
# Install build dependencies
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libportmidi-dev \
    libfreetype6-dev \
    build-essential

# Clone and build
git clone https://github.com/chris-t-hansen/gorillas-ports.git
cd gorillas-ports
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
./build.sh
```

#### Fedora
```bash
# Install build dependencies
sudo dnf install -y \
    python3-devel \
    python3-pip \
    SDL2-devel \
    SDL2_image-devel \
    SDL2_mixer-devel \
    SDL2_ttf-devel \
    portmidi-devel \
    freetype-devel \
    gcc

# Clone and build
git clone https://github.com/chris-t-hansen/gorillas-ports.git
cd gorillas-ports
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
./build.sh
```

#### openSUSE
```bash
# Install build dependencies
sudo zypper install -y \
    python3-devel \
    python3-pip \
    libSDL2-devel \
    libSDL2_image-devel \
    libSDL2_mixer-devel \
    libSDL2_ttf-devel \
    portmidi-devel \
    freetype2-devel \
    gcc

# Clone and build
git clone https://github.com/chris-t-hansen/gorillas-ports.git
cd gorillas-ports
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
./build.sh
```

#### Arch Linux / CachyOS / Manjaro
```bash
# Install build dependencies
sudo pacman -S --needed \
    python \
    python-pip \
    sdl2 \
    sdl2_image \
    sdl2_mixer \
    sdl2_ttf \
    portmidi \
    freetype2 \
    base-devel

# Clone and build
git clone https://github.com/chris-t-hansen/gorillas-ports.git
cd gorillas-ports
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
./build.sh
```

### For the End User (Running the Executable)

The user needs SDL2 runtime libraries installed:

#### Debian/Ubuntu
```bash
sudo apt-get install -y \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    libportmidi0
```

#### Fedora
```bash
sudo dnf install -y \
    SDL2 \
    SDL2_image \
    SDL2_mixer \
    SDL2_ttf \
    portmidi
```

#### openSUSE
```bash
sudo zypper install -y \
    libSDL2-2_0-0 \
    libSDL2_image-2_0-0 \
    libSDL2_mixer-2_0-0 \
    libSDL2_ttf-2_0-0 \
    libportmidi0
```

#### Arch Linux / CachyOS / Manjaro
```bash
sudo pacman -S --needed \
    sdl2 \
    sdl2_image \
    sdl2_mixer \
    sdl2_ttf \
    portmidi
```

## Distribution Strategies

### Strategy 1: Build on Oldest Target (Recommended)
Build the executable on the oldest distribution your friend uses. This maximizes compatibility.

Example: If targeting Debian 12, Fedora 38, and CachyOS, build on Debian 12.

### Strategy 2: Build on Each Distro
Build separate executables for each distribution. This ensures 100% compatibility but requires more work.

```bash
# On each system, run:
./build.sh
# Then rename the executable:
mv dist/gorillas dist/gorillas-debian  # or fedora, cachyos, etc.
```

### Strategy 3: Use Python (Fallback)
If the executable doesn't work, users can always run the game directly with Python:

```bash
git clone https://github.com/chris-t-hansen/gorillas-ports.git
cd gorillas-ports
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 game.py
```

## Troubleshooting

### "Error loading Python lib"
The executable was built with a newer Python version than available on the target system.
**Solution**: Rebuild on the target system or an older distribution.

### "libSDL2.so not found" or similar
SDL2 libraries are missing.
**Solution**: Install SDL2 runtime libraries (see "For the End User" section above).

### "glibc version not found"
The executable requires a newer glibc than available on the target system.
**Solution**: Rebuild on the target system or an older distribution with matching glibc version.

### "Segmentation fault"
Architecture mismatch or incompatible libraries.
**Solution**: Ensure you're using an executable built for the correct architecture (x86_64 vs aarch64).

## Checking Architecture

```bash
# Check your architecture
uname -m

# Check executable architecture
file dist/gorillas
```

Common architectures:
- `x86_64`: Most desktop/laptop Linux systems
- `aarch64` or `arm64`: Raspberry Pi 4, Apple Silicon (in VM), some ARM laptops

## Testing the Executable

After building, test thoroughly:

```bash
# Basic test
./dist/gorillas

# Test CGA mode
./dist/gorillas --cga

# Test with scaling
./dist/gorillas --scale 2

# Test with all options
./dist/gorillas --cga --scale 2 --speed 1.5
```

## Packaging for Distribution

### Simple Distribution (Single File)
```bash
# Just send the executable
scp dist/gorillas user@remote:/path/to/destination/
```

### Complete Package (with instructions)
```bash
# Create a tarball with everything
tar -czf gorillas-linux.tar.gz \
    dist/gorillas \
    README.md \
    DISTRO_GUIDE.md \
    requirements.txt

# Send the tarball
scp gorillas-linux.tar.gz user@remote:/path/to/destination/
```

### Including Runtime Instructions
Create a `RUN.sh` script:

```bash
#!/bin/bash
# Quick setup and run script for Gorillas

echo "=== Gorillas Game Runner ==="

# Check if SDL2 is installed
if ! ldconfig -p | grep -q libSDL2; then
    echo "Error: SDL2 libraries not found!"
    echo ""
    echo "Please install SDL2:"
    echo "  Debian/Ubuntu: sudo apt install libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0 libsdl2-ttf-2.0-0"
    echo "  Fedora: sudo dnf install SDL2 SDL2_image SDL2_mixer SDL2_ttf"
    echo "  Arch: sudo pacman -S sdl2 sdl2_image sdl2_mixer sdl2_ttf"
    exit 1
fi

# Run the game
./gorillas "$@"
```

## Summary

1. **Build on the oldest target distribution** for maximum compatibility
2. **Test on all target systems** before distributing
3. **Provide clear instructions** for installing SDL2 runtime libraries
4. **Include a fallback** Python installation method
5. **Document the architecture** (x86_64 vs aarch64) the executable was built for

## Current Build Info

- **Architecture**: Check with `file dist/gorillas`
- **Python Version**: Check with `python3 --version` (in the build environment)
- **Build Date**: Check file modification time of `dist/gorillas`

For questions or issues, refer to the main README.md or open an issue on GitHub.
