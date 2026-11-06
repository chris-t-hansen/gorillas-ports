#!/usr/bin/env python3
"""Diagnostic: decode EGA banana DATA longs and dump sprite bitmaps.

Run with:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/diag_banana.py

Produces ASCII art of each banana direction and saves PNGs to tests/output/.
"""

import os
import sys
import struct
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from qb_runtime.graphics import decode_put_data

# EGA banana DATA from gorilla.bas L135-143.
EGA_BANANAS = {
    "BananaLeft":  [458758, 202116096, 471604224, 943208448, 943208448, 943208448, 471604224, 202116096, 0],
    "BananaDown":  [262153, -2134835200, -2134802239, -2130771968, -2130738945, 8323072, 8323199, 4063232, 4063294],
    "BananaUp":    [262153, 4063232, 4063294, 8323072, 8323199, -2130771968, -2130738945, -2134835200, -2134802239],
    "BananaRight": [458758, -1061109760, -522133504, 1886416896, 1886416896, 1886416896, -522133504, -1061109760, 0],
}

# CGA banana DATA from gorilla.bas L125-133.
CGA_BANANAS = {
    "BananaLeft":  [327686, -252645316, 60],
    "BananaDown":  [196618, -1057030081, 49344],
    "BananaUp":    [196618, -1056980800, 63],
    "BananaRight": [327686, 1010580720, 240],
}


def to_unsigned32(v):
    """Convert a signed 32-bit int to unsigned."""
    return v & 0xFFFFFFFF


def dump_header(longs):
    """Decode and print the header word layout."""
    h = to_unsigned32(longs[0])
    w_lo = h & 0xFFFF
    h_hi = (h >> 16) & 0xFFFF
    # Try swapped too.
    print(f"  Header long: {h} = 0x{h:08X}")
    print(f"  Word0 (bits 0-15) = {w_lo}, Word1 (bits 16-31) = {h_hi}")
    print(f"  → Interpretation A: w={w_lo}, h={h_hi}")
    print(f"  → Interpretation B: w={h_hi}, h={w_lo}")

    # Check data size for both interpretations.
    data_bytes = len(longs[1:]) * 4
    for w, h, label in [(w_lo, h_hi, "A"), (h_hi, w_lo, "B")]:
        # EGA 4bpp, byte-aligned: 4 planes * ceil(w/8) bytes/row * h rows
        bpp4_ba = 4 * ((w + 7) // 8) * h
        # EGA 4bpp, word-aligned: 4 planes * 2 bytes/row * h rows
        bpp4_wa = 4 * 2 * h
        # CGA 2bpp, byte-aligned: 2 planes * ceil(w/8) bytes/row * h rows
        bpp2_ba = 2 * ((w + 7) // 8) * h
        print(f"  Interp {label} (w={w},h={h}): data={data_bytes}B, EGA-byte={bpp4_ba}B, EGA-word={bpp4_wa}B, CGA-byte={bpp2_ba}B")


def dump_sprite_ascii(sprite, name):
    """Print sprite as ASCII art (pixel values 0-15 → characters)."""
    h, w = sprite.shape
    print(f"\n  {name} ({w}x{h}):")
    # Color mapping: 0='.', 1-15 use various chars.
    chars = ".123456789ABCDEF"
    for row in range(h):
        line = ""
        for col in range(w):
            v = sprite[row, col]
            line += chars[v] if v < 16 else "?"
        print(f"    {line}")
    # Also print raw pixel values.
    print(f"  Raw values:")
    for row in range(h):
        print(f"    {list(sprite[row])}")


def save_sprite_png(sprite, filepath, palette=None):
    """Save a sprite as a scaled-up PNG for visual inspection."""
    import pygame
    h, w = sprite.shape
    scale = 16  # each pixel → 16x16 block

    if palette is None:
        # Default 16-color palette.
        palette = [
            (0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170),
            (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
            (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255),
            (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255),
        ]

    surf = pygame.Surface((w * scale, h * scale))
    surf.fill((40, 40, 40))  # dark gray background
    for row in range(h):
        for col in range(w):
            color = palette[sprite[row, col] & 0xF]
            pygame.draw.rect(surf, color, (col * scale, row * scale, scale, scale))
    pygame.image.save(surf, filepath)
    print(f"  Saved: {filepath}")


def main():
    import pygame
    pygame.init()

    os.makedirs("tests/output", exist_ok=True)

    print("=" * 60)
    print("EGA Banana Sprites")
    print("=" * 60)

    for name, longs in EGA_BANANAS.items():
        print(f"\n--- {name} ---")
        dump_header(longs)

        # Convert signed longs to unsigned for decode.
        unsigned_longs = [to_unsigned32(v) for v in longs]

        sprite = decode_put_data(unsigned_longs, bpp=4)
        dump_sprite_ascii(sprite, name)
        save_sprite_png(sprite, f"tests/output/ega_{name.lower()}.png")

    print("\n" + "=" * 60)
    print("CGA Banana Sprites")
    print("=" * 60)

    for name, longs in CGA_BANANAS.items():
        print(f"\n--- {name} ---")
        dump_header(longs)

        unsigned_longs = [to_unsigned32(v) for v in longs]

        sprite = decode_put_data(unsigned_longs, bpp=2)
        dump_sprite_ascii(sprite, name)
        save_sprite_png(sprite, f"tests/output/cga_{name.lower()}.png")


if __name__ == "__main__":
    main()
