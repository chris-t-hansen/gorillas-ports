# Cross-platform build script for Gorillas (PowerShell)
# Works on Windows, macOS, and Linux

$ErrorActionPreference = "Stop"

Write-Host "=== Gorillas Game Build Script (PowerShell) ===" -ForegroundColor Cyan
Write-Host ""

# Detect platform
$Platform = if ($IsWindows) { "windows" }
            elseif ($IsMacOS) { "macos" }
            elseif ($IsLinux) { "linux" }
            else { "unknown" }

Write-Host "Detected platform: $Platform ($PSVersionTable.OS)"
Write-Host ""

# Check Python
$Python = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $Python = "python"
} elseif (Get-Command "python3" -ErrorAction SilentlyContinue) {
    $Python = "python3"
} else {
    Write-Host "Error: Python not found. Please install Python 3.10+" -ForegroundColor Red
    if ($Platform -eq "windows") {
        Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    } elseif ($Platform -eq "macos") {
        Write-Host "Install via Homebrew: brew install python3" -ForegroundColor Yellow
    } else {
        Write-Host "Install via your package manager (python3 package)" -ForegroundColor Yellow
    }
    exit 1
}

$PythonVersion = & $Python --version
Write-Host "Using Python: $PythonVersion"
Write-Host ""

# Platform-specific setup
switch ($Platform) {
    "windows" {
        Write-Host "Windows build detected."
        Write-Host "pygame-ce includes pre-built SDL2 binaries for Windows."
        Write-Host "No additional system dependencies needed!"
        Write-Host ""
    }
    "macos" {
        Write-Host "macOS build detected."
        Write-Host "Make sure you have Homebrew and SDL2 installed:"
        Write-Host "  /bin/bash -c `"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)`"" -ForegroundColor Yellow
        Write-Host "  brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi" -ForegroundColor Yellow
        Write-Host ""
    }
    "linux" {
        Write-Host "Linux build detected."
        Write-Host "Make sure you have SDL2 development libraries installed:"
        Write-Host "  Debian/Ubuntu: sudo apt install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev" -ForegroundColor Yellow
        Write-Host "  Fedora: sudo dnf install SDL2-devel SDL2_image-devel SDL2_mixer-devel SDL2_ttf-devel" -ForegroundColor Yellow
        Write-Host "  Arch: sudo pacman -S sdl2 sdl2_image sdl2_mixer sdl2_ttf" -ForegroundColor Yellow
        Write-Host ""
    }
}

# Create venv if it doesn't exist
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    & $Python -m venv .venv
}

# Activate venv
Write-Host "Activating virtual environment..."
$ActivateScript = if ($Platform -eq "windows") { ".venv\Scripts\Activate.ps1" } else { ".venv/bin/activate.ps1" }

if (-not (Test-Path $ActivateScript)) {
    Write-Host "Error: Virtual environment activation script not found at $ActivateScript" -ForegroundColor Red
    exit 1
}

. $ActivateScript

# Upgrade pip
Write-Host "Upgrading pip..."
& $Python -m pip install --upgrade pip

# Install dependencies
Write-Host "Installing dependencies..."
& $Python -m pip install -r requirements.txt

# Install PyInstaller (pinned for reproducible builds)
Write-Host "Installing PyInstaller..."
& $Python -m pip install pyinstaller==6.22.3

Write-Host ""
Write-Host "Building standalone executable..."

# Clean previous builds
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

# Build
& pyinstaller gorillas.spec

# Determine output name and extension
$OutputName = "gorillas"
$Extension = ""
switch ($Platform) {
    "windows" { $OutputName = "gorillas"; $Extension = ".exe" }
    "macos" { $OutputName = "gorillas-macos" }
    "linux" { $OutputName = "gorillas-linux" }
}

$ExecutablePath = "dist/$OutputName$Extension"

if (Test-Path $ExecutablePath) {
    Write-Host ""
    Write-Host "=== Build Complete! ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Executable location: $ExecutablePath"
    Write-Host ""
    
    if ($Platform -eq "windows") {
        Write-Host "To test it:"
        Write-Host "  .\$ExecutablePath" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To test with CGA mode:"
        Write-Host "  .\$ExecutablePath --cga" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To test with scaling:"
        Write-Host "  .\$ExecutablePath --scale 2" -ForegroundColor Cyan
    } else {
        Write-Host "To test it:"
        Write-Host "  ./$ExecutablePath" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To test with CGA mode:"
        Write-Host "  ./$ExecutablePath --cga" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To test with scaling:"
        Write-Host "  ./$ExecutablePath --scale 2" -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Host "File size:"
    Get-Item $ExecutablePath | Select-Object Name, @{Name="Size (MB)";Expression={[math]::Round($_.Length/1MB, 2)}}
    
    Write-Host ""
    if ($Platform -eq "windows") {
        Write-Host "Note: The executable includes all dependencies and should run on any Windows 10/11 system." -ForegroundColor Yellow
        Write-Host "No additional installations required!" -ForegroundColor Green
    } elseif ($Platform -eq "macos") {
        Write-Host "Note: Users need SDL2 installed via Homebrew to run the executable." -ForegroundColor Yellow
    } else {
        Write-Host "Note: Users need SDL2 runtime libraries installed to run the executable." -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Error: Build failed. Check the output above for errors." -ForegroundColor Red
    exit 1
}
