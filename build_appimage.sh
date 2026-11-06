#!/bin/bash
# Build Gorillas AppImage
# Works on both x86_64 and aarch64 (ARM64)

set -e

echo "=== Building Gorillas AppImage ==="

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    ARCH_NAME="x86_64"
    APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
elif [ "$ARCH" = "aarch64" ]; then
    ARCH_NAME="aarch64"
    APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-aarch64.AppImage"
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

echo "Architecture: $ARCH_NAME"

# Check if we have the PyInstaller executable
if [ ! -f "dist/gorillas" ]; then
    echo "Error: dist/gorillas not found. Please run build.sh first."
    exit 1
fi

# Clean up previous AppImage build
rm -rf Gorillas.AppDir Gorillas-$ARCH_NAME.AppImage

# Create AppDir structure
echo "Creating AppDir structure..."
mkdir -p Gorillas.AppDir/usr/bin
mkdir -p Gorillas.AppDir/usr/lib
mkdir -p Gorillas.AppDir/usr/share/applications
mkdir -p Gorillas.AppDir/usr/share/icons/hicolor/256x256/apps

# Copy the executable
echo "Copying executable..."
cp dist/gorillas Gorillas.AppDir/usr/bin/gorillas
chmod +x Gorillas.AppDir/usr/bin/gorillas

# Bundle SDL2 libraries
echo "Bundling SDL2 libraries..."
for lib in libSDL2-2.0.so.0 libSDL2_image-2.0.so.0 libSDL2_mixer-2.0.so.0 libSDL2_ttf-2.0.so.0 libportmidi.so.0; do
    # Try to find the library
    LIB_PATH=$(ldconfig -p | grep "$lib" | head -1 | awk '{print $NF}' || true)
    
    if [ -n "$LIB_PATH" ] && [ -f "$LIB_PATH" ]; then
        echo "  Found $lib at $LIB_PATH"
        cp -L "$LIB_PATH" Gorillas.AppDir/usr/lib/
        
        # Also copy dependencies
        ldd "$LIB_PATH" | grep "=>" | awk '{print $3}' | while read dep; do
            if [ -f "$dep" ] && [[ ! "$dep" =~ ^/lib ]]; then
                echo "    Copying dependency: $dep"
                cp -L "$dep" Gorillas.AppDir/usr/lib/ || true
            fi
        done
    else
        echo "  Warning: $lib not found, skipping"
    fi
done

# Copy additional dependencies that PyInstaller might need
echo "Bundling additional dependencies..."
for lib in libfreetype.so.6 libpng16.so.16 libz.so.1 libbz2.so.1.0 libharfbuzz.so.0; do
    LIB_PATH=$(ldconfig -p | grep "$lib" | head -1 | awk '{print $NF}' || true)
    if [ -n "$LIB_PATH" ] && [ -f "$LIB_PATH" ]; then
        echo "  Copying $lib"
        cp -L "$LIB_PATH" Gorillas.AppDir/usr/lib/ || true
    fi
done

# Create AppRun script
echo "Creating AppRun script..."
cat > Gorillas.AppDir/AppRun << 'EOF'
#!/bin/bash
# Set up library path
HERE="$(dirname "$(readlink -f "${0}")")"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"

# Run the game
exec "${HERE}/usr/bin/gorillas" "$@"
EOF
chmod +x Gorillas.AppDir/AppRun

# Create desktop file
echo "Creating desktop file..."
cat > Gorillas.AppDir/gorillas.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Gorillas
Comment=QBASIC GORILLA.BAS faithful port
Exec=gorillas
Icon=gorillas
Categories=Game;
Terminal=true
EOF

# Create icon (use a simple PNG placeholder for now)
echo "Creating icon..."
if [ -f "icon.png" ]; then
    cp icon.png Gorillas.AppDir/usr/share/icons/hicolor/256x256/apps/gorillas.png
    cp icon.png Gorillas.AppDir/gorillas.png
else
    echo "  Warning: icon.png not found, using placeholder"
    # Create a simple placeholder icon using ImageMagick if available
    if command -v convert &> /dev/null; then
        convert -size 256x256 xc:#4a90e2 -gravity center -pointsize 48 -fill white -annotate 0 "G" Gorillas.AppDir/usr/share/icons/hicolor/256x256/apps/gorillas.png
        cp Gorillas.AppDir/usr/share/icons/hicolor/256x256/apps/gorillas.png Gorillas.AppDir/gorillas.png
    else
        # Create a minimal valid PNG (1x1 pixel)
        printf '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82' > Gorillas.AppDir/usr/share/icons/hicolor/256x256/apps/gorillas.png
        cp Gorillas.AppDir/usr/share/icons/hicolor/256x256/apps/gorillas.png Gorillas.AppDir/gorillas.png
    fi
fi

# Download appimagetool
echo "Downloading appimagetool..."
if [ ! -f "appimagetool" ]; then
    wget -q "$APPIMAGETOOL_URL" -O appimagetool
    chmod +x appimagetool
fi

# Build the AppImage
echo "Building AppImage..."
ARCH=$ARCH_NAME ./appimagetool Gorillas.AppDir Gorillas-$ARCH_NAME.AppImage

# Show result
echo ""
echo "=== AppImage Build Complete ==="
echo "Output: Gorillas-$ARCH_NAME.AppImage"
ls -lh Gorillas-$ARCH_NAME.AppImage
echo ""
echo "To test it:"
echo "  ./Gorillas-$ARCH_NAME.AppImage"
echo ""
echo "To make it executable for distribution:"
echo "  chmod +x Gorillas-$ARCH_NAME.AppImage"
