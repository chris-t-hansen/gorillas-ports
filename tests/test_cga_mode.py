#!/usr/bin/env python3
"""Test CGA mode rendering to verify 4-color graphics work correctly.

Run with:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_cga_mode.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()

from qb_runtime import screen as scr
from qb_runtime import text as txt
from qb_runtime import graphics as gfx
import numpy as np


def save_fb_png(name: str):
    """Save framebuffer as PNG."""
    fb = scr.fb()
    pal = scr.get_palette()
    h, w = fb.shape
    pal_arr = np.array(pal, dtype=np.uint8)
    rgb = pal_arr[fb]
    surf = pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))
    path = f"tests/output/{name}.png"
    os.makedirs("tests/output", exist_ok=True)
    pygame.image.save(surf, path)
    print(f"Saved: {path}")


print("=" * 60)
print("CGA Mode Test (SCREEN 1, 320x200, 4 colors)")
print("=" * 60)

# Test 1: Basic CGA mode initialization
print("\n[Test 1] Initialize SCREEN 1")
scr.screen(1)
print(f"  Mode: {scr.mode()}")
print(f"  Size: {scr.fb_width()}x{scr.fb_height()}")
print(f"  Palette: {scr.get_palette()}")
assert scr.mode() == 1
assert scr.fb_width() == 320
assert scr.fb_height() == 200
print("  ✓ PASS")

# Test 2: Palette 0 (cyan/magenta/white)
print("\n[Test 2] Set CGA Palette 0")
scr.set_cga_palette(0, 0)  # palette 0, black background
pal = scr.get_palette()
print(f"  Palette: {pal}")
# Should be: black, cyan, magenta, white
assert pal[0] == (0, 0, 0), f"Expected black, got {pal[0]}"
assert pal[1] == (0x55, 0xFF, 0xFF), f"Expected cyan, got {pal[1]}"
assert pal[2] == (0xFF, 0x55, 0xFF), f"Expected magenta, got {pal[2]}"
assert pal[3] == (0xFF, 0xFF, 0xFF), f"Expected white, got {pal[3]}"
print("  ✓ PASS")

# Test 3: Palette 1 (green/red/yellow)
print("\n[Test 3] Set CGA Palette 1")
scr.set_cga_palette(1, 0)  # palette 1, black background
pal = scr.get_palette()
print(f"  Palette: {pal}")
# Should be: black, green, red, yellow
assert pal[0] == (0, 0, 0), f"Expected black, got {pal[0]}"
assert pal[1] == (0x55, 0xFF, 0x55), f"Expected green, got {pal[1]}"
assert pal[2] == (0xFF, 0x55, 0x55), f"Expected red, got {pal[2]}"
assert pal[3] == (0xFF, 0xFF, 0x55), f"Expected yellow, got {pal[3]}"
print("  ✓ PASS")

# Test 4: Draw simple shapes in CGA mode
print("\n[Test 4] Draw shapes in CGA mode")
scr.screen(1)
scr.set_cga_palette(1, 0)  # green/red/yellow on black
scr.cls()

# Draw a box (color 1 = green)
gfx.line(50, 50, 150, 100, 1, b_flag=True)
# Draw a filled circle (color 2 = red)
gfx.circle(200, 75, 30, 2)
gfx.paint(200, 75, 2, 2)
# Draw a diagonal line (color 3 = yellow)
gfx.line(10, 10, 310, 190, 3)

save_fb_png("cga_test_shapes")
print("  ✓ PASS")

# Test 5: Text in CGA mode
print("\n[Test 5] Text rendering in CGA mode")
scr.screen(1)
scr.set_cga_palette(1, 0)
scr.cls()
txt.init()

txt.locate(1, 1)
txt.color(1, 0)  # green text
txt.print_("CGA MODE TEST")

txt.locate(3, 1)
txt.color(2, 0)  # red text
txt.print_("Palette 1: Green/Red/Yellow")

txt.locate(5, 1)
txt.color(3, 0)  # yellow text
txt.print_("320x200, 4 colors")

scr.present()
save_fb_png("cga_test_text")
print("  ✓ PASS")

# Test 6: Load and decode CGA banana sprites
print("\n[Test 6] CGA banana sprites")
from qb_runtime.graphics import decode_put_data

# CGA banana DATA from gorilla.bas
cga_left = [327686, -252645316, 60]
cga_down = [196618, -1057030081, 49344]

u32 = lambda longs: [v & 0xFFFFFFFF for v in longs]

lb = decode_put_data(u32(cga_left), bpp=2)
db = decode_put_data(u32(cga_down), bpp=2)

print(f"  BananaLeft shape: {lb.shape}")
print(f"  BananaDown shape: {db.shape}")

# Should be 6x5 and 10x3
assert lb.shape == (5, 6), f"Expected (5, 6), got {lb.shape}"
assert db.shape == (3, 10), f"Expected (3, 10), got {db.shape}"

# Draw them on screen
scr.screen(1)
scr.set_cga_palette(1, 0)
scr.cls()
gfx.put_sprite(50, 50, lb, action="PSET")
gfx.put_sprite(100, 50, db, action="PSET")

save_fb_png("cga_test_bananas")
print("  ✓ PASS")

print("\n" + "=" * 60)
print("All CGA mode tests PASSED")
print("=" * 60)
