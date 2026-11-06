# Build Guide - Cross-Platform Instructions

This guide explains how to build and distribute the Gorillas game executable across different operating systems.

## Supported Platforms

| Platform | Build System | Output | Status |
|----------|-------------|--------|--------|
| Linux (Debian/Ubuntu/Fedora/Arch/SUSE) | `./build.sh` | `gorillas-linux` | ✅ Tested |
| macOS (Intel & Apple Silicon) | `./build.sh` or `pwsh build.ps1` | `gorillas-macos` | ✅ Supported |
| Windows 10/11 | `build.bat` or `pwsh build.ps1` | `gorillas.exe` | ✅ Supported |
| FreeBSD/OpenBSD/NetBSD | `./build.sh` or `pwsh build.ps1` | `gorillas-{bsd}` | ⚠️ Experimental |

## Quick Start

### Choose Your Build Method

**Option 1: Platform-specific scripts (Recommended)**
- **Windows**: Double-click `build.bat` or run in Command Prompt
- **macOS/Linux/BSD**: Run `./build.sh` in Terminal

**Option 2: PowerShell (Cross-platform)**
- **All platforms**: Run `pwsh build.ps1` (requires PowerShell 7+)

## Platform-Specific Instructions

### Windows 10/11

#### Prerequisites
1. **Python 3.10+**: Download from [python.org](https://www.python.org/downloads/)
   - ⚠️ **Important**: Check "Add Python to PATH" during installation
2. **No additional dependencies needed** - pygame-ce includes pre-built SDL2 binaries

#### Build Steps

**Method 1: Batch Script (Easiest)**
```cmd
# Double-click build.bat, or run in Command Prompt:
build.bat
```

**Method 2: PowerShell**
```powershell
# Open PowerShell and run:
pwsh build.ps1
```

**Method 3: Manual**
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller gorillas.spec
```

#### Output
- Location: `dist/gorillas.exe`
- Size: ~30-40 MB
- **Self-contained**: Includes all dependencies, no additional installations needed for users

#### Distribution
Just send the `.exe` file! Users can run it directly on any Windows 10/11 system.

---

### macOS (Intel & Apple Silicon)

#### Prerequisites
1. **Python 3.10+**: Install via [python.org](https://www.python.org/downloads/macos/) or Homebrew
2. **Homebrew**: Install if not present
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. **SDL2 libraries**:
   ```bash
   brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi
   ```

#### Build Steps

**Method 1: Shell Script**
```bash
chmod +x build.sh
./build.sh
```

**Method 2: PowerShell**
```bash
# Install PowerShell if needed: brew install --cask powershell
pwsh build.ps1
```

**Method 3: Manual**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller gorillas.spec
```

#### Output
- Location: `dist/gorillas-macos`
- Size: ~40-50 MB
- **Runtime dependency**: Users need SDL2 installed via Homebrew

#### Distribution
Send the executable + installation instructions for SDL2:
```bash
# Users run this first:
brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi

# Then run the game:
./gorillas-macos
```

#### Apple Silicon Notes
- Builds on M1/M2/M3 Macs will create ARM64 executables
- These won't run on Intel Macs (and vice versa)
- For universal binaries, build separately on each architecture

---

### Linux

#### Prerequisites by Distribution

**Debian/Ubuntu/Pop!_OS**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    libportmidi-dev libfreetype6-dev build-essential
```

**Fedora/RHEL/CentOS**
```bash
sudo dnf install -y python3-devel python3-pip gcc \
    SDL2-devel SDL2_image-devel SDL2_mixer-devel SDL2_ttf-devel \
    portmidi-devel freetype-devel
```

**Arch Linux/Manjaro/CachyOS**
```bash
sudo pacman -S python python-pip base-devel \
    sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi freetype2
```

**openSUSE**
```bash
sudo zypper install -y python3-devel python3-pip gcc \
    libSDL2-devel libSDL2_image-devel libSDL2_mixer-devel libSDL2_ttf-devel \
    portmidi-devel freetype2-devel
```

#### Build Steps

```bash
chmod +x build.sh
./build.sh
```

#### Output
- Location: `dist/gorillas-linux`
- Size: ~30-40 MB
- **Runtime dependency**: Users need SDL2 runtime libraries

#### Distribution
Send the executable + instructions for SDL2:
```bash
# Debian/Ubuntu users:
sudo apt install libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0 libsdl2-ttf-2.0-0

# Fedora users:
sudo dnf install SDL2 SDL2_image SDL2_mixer SDL2_ttf

# Arch users:
sudo pacman -S sdl2 sdl2_image sdl2_mixer sdl2_ttf
```

---

### FreeBSD / OpenBSD / NetBSD

#### Prerequisites

**FreeBSD**
```bash
pkg install python3 py311-pip sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi freetype2
```

**OpenBSD**
```bash
pkg_add python sdl2 sdl2-image sdl2-mixer sdl2-ttf portmidi freetype
```

**NetBSD**
```bash
pkgin install python311 py311-pip SDL2 SDL2_image SDL2_mixer SDL2_ttf portmidi freetype2
```

#### Build Steps

```bash
chmod +x build.sh
./build.sh
```

#### Output
- Location: `dist/gorillas-{freebsd,openbsd,netbsd}`
- Size: ~30-40 MB
- **Runtime dependency**: Users need SDL2 packages installed

#### Distribution
```bash
# FreeBSD users:
pkg install sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi

# Then run:
./gorillas-freebsd
```

## Cross-Platform Compatibility

### Understanding Compatibility

PyInstaller executables bundle Python and most dependencies, but still rely on:
- **Windows**: SDL2 DLLs (bundled by pygame-ce)
- **macOS/Linux/BSD**: System SDL2 libraries

### Key Compatibility Rules

1. **Same OS required**: Windows executables won't run on macOS/Linux
2. **Same architecture**: x86_64 executables won't run on ARM64 (except via Rosetta on macOS)
3. **Build on oldest target**: For Linux, build on oldest distro you want to support (glibc compatibility)
4. **SDL2 version**: Build with SDL2 version similar to what users will have

### Recommended Build Strategy

**For maximum compatibility:**

1. **Windows**: Build on Windows 10 (works on 10 and 11)
2. **macOS**: Build on oldest macOS you want to support (e.g., macOS 11 Big Sur)
3. **Linux**: Build on Debian Stable or Ubuntu LTS for broadest compatibility
4. **BSD**: Build on the specific BSD variant

## Troubleshooting

### Common Issues

#### Windows: "Python not found"
**Solution**: Reinstall Python and check "Add Python to PATH"

#### macOS: "SDL2 not found" during build
**Solution**: Install SDL2 via Homebrew:
```bash
brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi
```

#### Linux: "glibc version not found"
**Cause**: Executable built on newer distro than target
**Solution**: Rebuild on target distro or older distro

#### All platforms: "Module not found: pygame_ce"
**Solution**: Make sure you're in the virtual environment:
```bash
# Windows
.venv\Scripts\activate

# macOS/Linux/BSD
source .venv/bin/activate
```

#### Executable crashes immediately
**Check**:
1. Run from command line to see error messages
2. Verify SDL2 libraries are installed
3. Check architecture matches (x86_64 vs ARM64)

### Debugging Tips

```bash
# Run with verbose output
./dist/gorillas-linux --debug

# Check library dependencies (Linux)
ldd dist/gorillas-linux

# Check library dependencies (macOS)
otool -L dist/gorillas-macos

# Check library dependencies (Windows)
# Use Dependencies: https://github.com/lucasg/Dependencies
```

## Distribution Strategies

### Strategy 1: GitHub Releases (Recommended)
Build on each platform and upload to GitHub Releases:
```bash
# Create release on GitHub
# Upload:
# - gorillas.exe (Windows)
# - gorillas-macos (macOS)
# - gorillas-linux (Linux)
# - gorillas-freebsd (FreeBSD)
```

### Strategy 2: Build from Source
Users clone the repo and build locally:
```bash
git clone https://github.com/chris-t-hansen/gorillas-ports.git
cd gorillas-ports
./build.sh  # or build.bat on Windows
```

### Strategy 3: Hybrid Approach
- Provide Windows `.exe` (most users, no dependencies)
- Provide build instructions for macOS/Linux/BSD

## Testing Your Build

After building, test thoroughly:

```bash
# Basic test
./dist/gorillas-{platform}

# Test CGA mode
./dist/gorillas-{platform} --cga

# Test with scaling
./dist/gorillas-{platform} --scale 2

# Test with all options
./dist/gorillas-{platform} --cga --scale 2 --speed 1.5 --mute
```

## File Sizes (Approximate)

| Platform | Size | Notes |
|----------|------|-------|
| Windows | 30-40 MB | Includes SDL2 DLLs |
| macOS | 40-50 MB | Larger Python runtime |
| Linux | 30-40 MB | Varies by distro |
| BSD | 30-40 MB | Similar to Linux |

## Summary

1. **Windows**: Easiest - just run `build.bat`, produces self-contained `.exe`
2. **macOS**: Install SDL2 via Homebrew, run `./build.sh`
3. **Linux**: Install SDL2 dev packages, run `./build.sh`
4. **BSD**: Install SDL2 packages, run `./build.sh`
5. **Cross-platform**: Use `pwsh build.ps1` if PowerShell is installed

## Need Help?

- Check the main `README.md` for game instructions
- Open an issue on GitHub with your platform and error details
- Include output from running the executable in a terminal

## Current Build Info

Check your build:
```bash
# Architecture
uname -m  # Linux/macOS/BSD
echo %PROCESSOR_ARCHITECTURE%  # Windows

# Executable architecture
file dist/gorillas-*  # Linux/macOS/BSD
```

Common architectures:
- `x86_64` / `AMD64`: Most desktop/laptop systems
- `aarch64` / `arm64`: Raspberry Pi 4, Apple Silicon, some ARM laptops
