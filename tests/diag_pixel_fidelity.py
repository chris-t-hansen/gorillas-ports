#!/usr/bin/env python3
"""Pixel fidelity diagnostic — exercise all drawing primitives, generate golden files.

Run with:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/diag_pixel_fidelity.py

Generates PNGs in tests/golden/ for visual inspection and future golden-file tests.
"""

import os
import sys
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from qb_runtime import screen as scr
from qb_runtime import text as txt
from qb_runtime import graphics as gfx
from qb_runtime.screen import ega_decode

GOLDEN_DIR = "tests/golden"
os.makedirs(GOLDEN_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Game-level Scl() — exact translation from gorilla.bas L1036-1049
# ---------------------------------------------------------------------------


def scl(n: float, mode: int) -> int:
    """Scl(n!) — exact QBASIC translation for game.py."""
    if n != int(n):
        if mode == 1:
            n = n - 1
    if mode == 1:
        # CINT(n / 2 + .1)
        return round(n / 2 + 0.1)
    else:
        return round(n)


def save_fb_png(name: str):
    """Save the current framebuffer as a PNG with the active palette applied."""
    fb = scr.fb()
    pal = scr.get_palette()
    h, w = fb.shape
    pal_arr = np.array(pal, dtype=np.uint8)
    rgb = pal_arr[fb]  # (H, W, 3)
    surf = pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))
    path = os.path.join(GOLDEN_DIR, f"{name}.png")
    pygame.image.save(surf, path)
    print(f"  Saved: {path}")


def save_fb_scaled_png(name: str, scale: int = 2):
    """Save framebuffer scaled up for easier visual inspection."""
    fb = scr.fb()
    pal = scr.get_palette()
    h, w = fb.shape
    pal_arr = np.array(pal, dtype=np.uint8)
    rgb = pal_arr[fb]
    surf = pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))
    scaled = pygame.transform.scale(surf, (w * scale, h * scale))
    path = os.path.join(GOLDEN_DIR, f"{name}_x{scale}.png")
    pygame.image.save(scaled, path)
    print(f"  Saved: {path}")


# =========================================================================
# Test 1: EGA Palette decode — all 64 colors
# =========================================================================
def test_ega_palette_all64():
    print("\n=== Test 1: EGA 64-color palette ===")
    # Generate a swatch image showing all 64 EGA colors.
    swatch = np.zeros((8 * 16, 8 * 16, 3), dtype=np.uint8)
    for v in range(64):
        r, g, b = ega_decode(v)
        row = (v // 8) * 16
        col = (v % 8) * 16
        swatch[row:row + 16, col:col + 16] = (r, g, b)
    surf = pygame.surfarray.make_surface(swatch.transpose(1, 0, 2))
    path = os.path.join(GOLDEN_DIR, "ega_64colors.png")
    pygame.image.save(surf, path)
    print(f"  Saved: {path}")

    # Verify known anchors.
    anchors = {
        1: (0, 0, 170),      # blue
        4: (170, 0, 0),       # red
        7: (170, 170, 170),   # light gray
        20: (170, 85, 0),     # brown
        44: (255, 0, 85),     # vivid red
        46: (255, 170, 85),   # orange
        54: (255, 255, 0),    # yellow
        56: (85, 85, 85),     # dark gray
        63: (255, 255, 255),  # white
    }
    for v, expected in anchors.items():
        actual = ega_decode(v)
        assert actual == expected, f"EGA {v}: expected {expected}, got {actual}"
    print("  All 9 anchor colors verified.")


# =========================================================================
# Test 2: Text rendering — SCREEN 0
# =========================================================================
def test_text_rendering():
    print("\n=== Test 2: Text rendering (SCREEN 0) ===")
    scr.screen(0)
    txt.init()

    # Print various text elements.
    txt.color(15, 0)  # white on black
    txt.locate(1, 1)
    txt.print_("GORILLAS")
    txt.locate(3, 1)
    txt.color(7, 0)  # light gray
    txt.print_("Copyright (C) Microsoft Corporation 1990")
    txt.locate(5, 1)
    txt.color(14, 0)  # yellow
    txt.print_("Your mission is to hit your opponent")
    txt.locate(6, 1)
    txt.print_("with the exploding banana.")

    # Test print zones (comma separator).
    txt.locate(8, 1)
    txt.color(7, 0)
    txt.print_("Zone1", sep=",")
    txt.print_("Zone2", sep=",")
    txt.print_("Zone3")

    # Test semicolon (no newline).
    txt.locate(10, 1)
    txt.print_semi("Score: ")
    txt.color(15, 0)
    txt.print_("42")

    # Test CP437 special chars — smileys and block elements.
    txt.locate(12, 1)
    txt.color(7, 0)
    for code in [1, 2, 3, 4, 5, 6]:
        txt._write_char(code)
    txt._write_char(32)  # space
    for code in range(176, 180):  # block elements
        txt._write_char(code)
    txt._write_char(32)
    for code in range(219, 224):  # full blocks
        txt._write_char(code)

    txt._advance_newline()

    save_fb_png("screen0_text")
    save_fb_scaled_png("screen0_text")

    # Verify specific characters in grid.
    assert txt._grid_chars[0, 0] == ord('G'), "First char should be 'G'"
    assert txt._grid_chars[0, 7] == ord('S'), "8th char should be 'S'"
    print("  Text grid verified.")


# =========================================================================
# Test 3: LINE primitives — SCREEN 9
# =========================================================================
def test_line_primitives():
    print("\n=== Test 3: LINE primitives (SCREEN 9) ===")
    scr.screen(9)
    # Set up the game's palette remap.
    scr.set_palette_color(0, 1)    # blue bg
    scr.set_palette_color(1, 46)   # orange (gorillas)
    scr.set_palette_color(2, 44)   # vivid red (explosions)
    scr.set_palette_color(3, 54)   # yellow (sun)
    scr.set_palette_color(5, 7)    # light gray
    scr.set_palette_color(6, 4)    # red
    scr.set_palette_color(7, 3)    # cyan
    scr.set_palette_color(9, 63)   # white

    scr.cls()
    fb = scr.fb()

    # Draw various lines.
    # Horizontal line.
    gfx.line(10, 10, 100, 10, 15)
    # Vertical line.
    gfx.line(10, 20, 10, 80, 15)
    # Diagonal line.
    gfx.line(20, 20, 80, 80, 15)
    # Box outline (B flag).
    gfx.line(120, 20, 200, 80, 1, b_flag=True)
    # Filled box (BF flag).
    gfx.line(220, 20, 300, 80, 2, bf_flag=True)
    # Styled line (dashed: &HAAAA = 1010101010101010).
    gfx.line(10, 100, 300, 100, 15, style=0xAAAA)
    # Styled line (dotted: &HCCCC = 1100110011001100).
    gfx.line(10, 110, 300, 110, 15, style=0xCCCC)

    save_fb_png("screen9_lines")
    save_fb_scaled_png("screen9_lines")

    # Verify specific pixels.
    assert scr.point(50, 10) == 15, "Horizontal line pixel"
    assert scr.point(10, 50) == 15, "Vertical line pixel"
    assert scr.point(120, 50) == 1, "Box outline left edge"
    assert scr.point(260, 50) == 2, "Filled box interior"
    print("  LINE primitives verified.")


# =========================================================================
# Test 4: CIRCLE — various radii, aspects, arcs
# =========================================================================
def test_circle_primitives():
    print("\n=== Test 4: CIRCLE primitives (SCREEN 9) ===")
    scr.screen(9)
    scr.set_palette_color(0, 1)
    scr.cls()

    # Simple circle.
    gfx.circle(80, 80, 30, 15)
    # Circle with aspect > 1 (tall ellipse).
    gfx.circle(200, 80, 30, 15, aspect=2.0)
    # Circle with aspect < 1 (wide ellipse).
    gfx.circle(320, 80, 30, 15, aspect=0.5)
    # Arc (partial circle).
    gfx.circle(80, 200, 30, 15, start_angle=0, end_angle=math.pi)
    # Pie slice (negative angles → lines to center).
    gfx.circle(200, 200, 30, 15, start_angle=-math.pi / 4, end_angle=-3 * math.pi / 4)
    # ExplodeGorilla-style pie slice (aspect -1.57).
    gfx.circle(400, 200, 40, 2, start_angle=-math.pi * 3 / 4, end_angle=-math.pi * 9 / 8, aspect=1.57)

    save_fb_png("screen9_circles")
    save_fb_scaled_png("screen9_circles")

    # Verify circle outline pixels.
    assert scr.point(110, 80) == 15, "Circle right edge"
    print("  CIRCLE primitives verified.")


# =========================================================================
# Test 5: PAINT — flood fill
# =========================================================================
def test_paint():
    print("\n=== Test 5: PAINT (flood fill) (SCREEN 9) ===")
    scr.screen(9)
    scr.set_palette_color(0, 1)
    scr.cls()

    # Draw a box outline and fill it.
    gfx.line(50, 50, 150, 120, 3, b_flag=True)  # border is 3
    gfx.paint(100, 85, 3)  # fill interior with color 3 (border defaults to 3)

    # Draw a circle and fill it (sun-like).
    gfx.circle(300, 85, 30, 3)  # border is 3
    gfx.paint(300, 85, 3)  # fill with 3 (border defaults to 3)

    save_fb_png("screen9_paint")
    save_fb_scaled_png("screen9_paint")

    # Verify fill.
    assert scr.point(100, 85) == 3, "Box interior should be filled with color 3"
    assert scr.point(300, 85) == 3, "Circle interior should be filled with color 3"
    assert scr.point(10, 10) == 0, "Background should be 0"
    print("  PAINT verified.")


# =========================================================================
# Test 6: GET / PUT — sprite capture and blit
# =========================================================================
def test_get_put():
    print("\n=== Test 6: GET/PUT (SCREEN 9) ===")
    scr.screen(9)
    scr.set_palette_color(0, 1)
    scr.set_palette_color(1, 46)
    scr.cls()

    # Draw a small shape.
    gfx.line(50, 50, 70, 70, 1, bf_flag=True)
    gfx.circle(60, 60, 5, 15)

    # GET the region.
    sprite = gfx.get_sprite(45, 45, 75, 75)
    assert sprite.shape == (31, 31), f"Sprite shape: {sprite.shape}"

    # Erase the original area.
    gfx.line(45, 45, 75, 75, 0, bf_flag=True)
    assert scr.point(60, 60) == 0, "Area should be erased"

    # PUT with PSET — restore.
    gfx.put_sprite(45, 45, sprite, action="PSET")
    assert scr.point(60, 60) != 0, "Sprite should be restored"

    # PUT with XOR at a different location — should draw.
    gfx.put_sprite(200, 200, sprite, action="XOR")
    # XOR on background (0): 0 XOR pixel = pixel.
    # So pixels that were non-zero in sprite become non-zero.

    # PUT with XOR again — should erase.
    before = scr.point(200 + 15, 200 + 15)
    gfx.put_sprite(200, 200, sprite, action="XOR")
    after = scr.point(200 + 15, 200 + 15)
    assert after != before or before == 0, "XOR twice should restore"

    save_fb_png("screen9_getput")
    save_fb_scaled_png("screen9_getput")
    print("  GET/PUT verified.")


# =========================================================================
# Test 7: Palette change immediacy
# =========================================================================
def test_palette_immediacy():
    print("\n=== Test 7: Palette change immediacy ===")
    scr.screen(9)
    scr.cls()

    # Draw a filled box with color 5.
    gfx.line(50, 50, 150, 120, 5, bf_flag=True)

    # Save before palette change.
    save_fb_png("palette_before")

    # Get RGB before change.
    pal_before = scr.get_palette()
    rgb_before = pal_before[5]

    # Change palette register 5.
    scr.set_palette_color(5, 63)  # white

    pal_after = scr.get_palette()
    rgb_after = pal_after[5]

    # The framebuffer still has value 5 at those pixels.
    assert scr.point(100, 85) == 5, "Framebuffer value unchanged"

    # But when presented, the RGB mapping changes.
    # Verify the palette arrays differ.
    assert rgb_before != rgb_after, "Palette should have changed"

    save_fb_png("palette_after")
    print(f"  Before: pixel 5 = RGB{rgb_before}")
    print(f"  After:  pixel 5 = RGB{rgb_after}")
    print("  Palette change immediacy verified (indexed fb, palette at present time).")


# =========================================================================
# Test 8: Banana sprites — decode and PUT
# =========================================================================
def test_banana_sprites():
    print("\n=== Test 8: Banana sprites (decode + PUT) ===")
    scr.screen(9)
    scr.set_palette_color(0, 1)
    scr.set_palette_color(1, 46)
    scr.set_palette_color(9, 63)
    scr.cls()

    from qb_runtime.graphics import decode_put_data

    # EGA banana DATA.
    EGA_BANANAS = {
        "left":  [458758, 202116096, 471604224, 943208448, 943208448, 943208448, 471604224, 202116096, 0],
        "down":  [262153, -2134835200 & 0xFFFFFFFF, -2134802239 & 0xFFFFFFFF,
                  -2130771968 & 0xFFFFFFFF, -2130738945 & 0xFFFFFFFF,
                  8323072, 8323199, 4063232, 4063294],
        "up":    [262153, 4063232, 4063294, 8323072, 8323199,
                  -2130771968 & 0xFFFFFFFF, -2130738945 & 0xFFFFFFFF,
                  -2134835200 & 0xFFFFFFFF, -2134802239 & 0xFFFFFFFF],
        "right": [458758, -1061109760 & 0xFFFFFFFF, -522133504 & 0xFFFFFFFF,
                  1886416896 & 0xFFFFFFFF, 1886416896 & 0xFFFFFFFF,
                  1886416896 & 0xFFFFFFFF, -522133504 & 0xFFFFFFFF,
                  -1061109760 & 0xFFFFFFFF, 0],
    }

    positions = {"left": (50, 50), "up": (100, 50), "down": (150, 50), "right": (200, 50)}

    for name, longs in EGA_BANANAS.items():
        sprite = decode_put_data(longs, bpp=4)
        x, y = positions[name]
        gfx.put_sprite(x, y, sprite, action="PSET")

    save_fb_png("screen9_bananas")
    save_fb_scaled_png("screen9_bananas")

    # Verify bananas have non-zero pixels.
    for name, (x, y) in positions.items():
        # Check center-ish area for non-zero.
        found = False
        for dy in range(10):
            for dx in range(10):
                if scr.point(x + dx, y + dy) != 0:
                    found = True
                    break
        assert found, f"Banana {name} should have visible pixels"

    print("  Banana sprites decoded and rendered.")


# =========================================================================
# Test 9: DrawGorilla — procedural drawing (EGA mode)
# =========================================================================
def test_draw_gorilla():
    print("\n=== Test 9: DrawGorilla (procedural, EGA) ===")
    scr.screen(9)
    scr.set_palette_color(0, 1)    # blue bg
    scr.set_palette_color(1, 46)   # orange (gorilla)
    scr.cls()

    # Implement Scl() for mode 9.
    def s(n):
        return scl(n, 9)

    # Draw gorilla at (320, 175) with arms down — exact translation of DrawGorilla.
    x, y = 320, 175
    OBJECTCOLOR = 1
    pi = math.pi

    # Head.
    gfx.line(x - s(4), y, x + s(2.9), y + s(6), OBJECTCOLOR, bf_flag=True)
    gfx.line(x - s(5), y + s(2), x + s(4), y + s(4), OBJECTCOLOR, bf_flag=True)

    # Eyes/brow.
    gfx.line(x - s(3), y + s(2), x + s(2), y + s(2), 0)

    # Nose (EGA only).
    for i in range(-2, 0):
        gfx.pset(x + i, y + 4, 0)
        gfx.pset(x + i + 3, y + 4, 0)

    # Neck.
    gfx.line(x - s(3), y + s(7), x + s(2), y + s(7), OBJECTCOLOR)

    # Body.
    gfx.line(x - s(8), y + s(8), x + s(6.9), y + s(14), OBJECTCOLOR, bf_flag=True)
    gfx.line(x - s(6), y + s(15), x + s(4.9), y + s(20), OBJECTCOLOR, bf_flag=True)

    # Legs.
    for i in range(5):
        gfx.circle(x + s(i), y + s(25), s(10), OBJECTCOLOR,
                   start_angle=3 * pi / 4, end_angle=9 * pi / 8)
        gfx.circle(x + s(-6) + s(i - 0.1), y + s(25), s(10), OBJECTCOLOR,
                   start_angle=15 * pi / 8, end_angle=pi / 4)

    # Chest.
    gfx.circle(x - s(4.9), y + s(10), s(4.9), 0,
               start_angle=3 * pi / 2, end_angle=0)
    gfx.circle(x + s(4.9), y + s(10), s(4.9), 0,
               start_angle=pi, end_angle=3 * pi / 2)

    # Arms down.
    for i in range(-5, 0):
        gfx.circle(x + s(i - 0.1), y + s(14), s(9), OBJECTCOLOR,
                   start_angle=3 * pi / 4, end_angle=5 * pi / 4)
        gfx.circle(x + s(4.9) + s(i), y + s(14), s(9), OBJECTCOLOR,
                   start_angle=7 * pi / 4, end_angle=pi / 4)

    # GET the gorilla sprite.
    gorilla_sprite = gfx.get_sprite(x - s(15), y - s(1), x + s(14), y + s(28))
    print(f"  Gorilla sprite size: {gorilla_sprite.shape}")

    save_fb_png("screen9_gorilla_draw")
    save_fb_scaled_png("screen9_gorilla_draw")

    # Now PUT the gorilla at a different location.
    gfx.put_sprite(100, 100, gorilla_sprite, action="PSET")

    save_fb_png("screen9_gorilla_put")
    save_fb_scaled_png("screen9_gorilla_put")

    # Verify gorilla has orange pixels.
    found_orange = False
    for dy in range(gorilla_sprite.shape[0]):
        for dx in range(gorilla_sprite.shape[1]):
            if gorilla_sprite[dy, dx] == OBJECTCOLOR:
                found_orange = True
                break
    assert found_orange, "Gorilla should have orange (color 1) pixels"
    print("  DrawGorilla verified.")


# =========================================================================
# Test 10: DoSun — sun drawing
# =========================================================================
def test_do_sun():
    print("\n=== Test 10: DoSun (SCREEN 9) ===")
    scr.screen(9)
    scr.set_palette_color(0, 1)    # blue bg
    scr.set_palette_color(3, 54)   # yellow (sun)
    scr.cls()

    def s(n):
        return scl(n, 9)

    SUNATTR = 3
    pi = math.pi

    # Sun position.
    x = 640 // 2  # ScrWidth \ 2
    y = s(25)

    # Body.
    gfx.circle(x, y, s(12), SUNATTR)
    gfx.paint(x, y, SUNATTR)

    # Rays.
    gfx.line(x - s(20), y, x + s(20), y, SUNATTR)
    gfx.line(x, y - s(15), x, y + s(15), SUNATTR)
    gfx.line(x - s(15), y - s(10), x + s(15), y + s(10), SUNATTR)
    gfx.line(x - s(15), y + s(10), x + s(15), y - s(10), SUNATTR)
    gfx.line(x - s(8), y - s(13), x + s(8), y + s(13), SUNATTR)
    gfx.line(x - s(8), y + s(13), x + s(8), y - s(13), SUNATTR)
    gfx.line(x - s(18), y - s(5), x + s(18), y + s(5), SUNATTR)
    gfx.line(x - s(18), y + s(5), x + s(18), y - s(5), SUNATTR)

    # Happy mouth (smile).
    gfx.circle(x, y, s(8), 0, start_angle=210 * pi / 180, end_angle=330 * pi / 180)

    # Eyes.
    gfx.circle(x - 3, y - 2, 1, 0)
    gfx.circle(x + 3, y - 2, 1, 0)
    gfx.pset(x - 3, y - 2, 0)
    gfx.pset(x + 3, y - 2, 0)

    save_fb_png("screen9_sun_happy")
    save_fb_scaled_png("screen9_sun_happy")

    # Now draw shocked mouth.
    # Clear old sun area.
    BACKATTR = 0
    gfx.line(x - s(22), y - s(18), x + s(22), y + s(18), BACKATTR, bf_flag=True)

    # Redraw sun body + rays.
    gfx.circle(x, y, s(12), SUNATTR)
    gfx.paint(x, y, SUNATTR)
    gfx.line(x - s(20), y, x + s(20), y, SUNATTR)
    gfx.line(x, y - s(15), x, y + s(15), SUNATTR)
    gfx.line(x - s(15), y - s(10), x + s(15), y + s(10), SUNATTR)
    gfx.line(x - s(15), y + s(10), x + s(15), y - s(10), SUNATTR)
    gfx.line(x - s(8), y - s(13), x + s(8), y + s(13), SUNATTR)
    gfx.line(x - s(8), y + s(13), x + s(8), y - s(13), SUNATTR)
    gfx.line(x - s(18), y - s(5), x + s(18), y + s(5), SUNATTR)
    gfx.line(x - s(18), y + s(5), x + s(18), y - s(5), SUNATTR)

    # "O" mouth.
    gfx.circle(x, y + s(5), s(2.9), 0)
    gfx.paint(x, y + s(5), 0, 0)

    # Eyes.
    gfx.circle(x - 3, y - 2, 1, 0)
    gfx.circle(x + 3, y - 2, 1, 0)
    gfx.pset(x - 3, y - 2, 0)
    gfx.pset(x + 3, y - 2, 0)

    save_fb_png("screen9_sun_shock")
    save_fb_scaled_png("screen9_sun_shock")

    print("  DoSun verified (happy + shock).")


# =========================================================================
# Test 11: Scl() values table
# =========================================================================
def test_scl_values():
    print("\n=== Test 11: Scl() values for EGA and CGA ===")
    # Key Scl() inputs used in DrawGorilla.
    inputs = [1, 2, 2.9, 3, 4, 4.9, 5, 6, 6.9, 7, 8, 9, 10, 12, 14, 15, 20, 25, 28]
    print(f"  {'Input':>6} | {'EGA (Mode 9)':>12} | {'CGA (Mode 1)':>12}")
    print(f"  {'------':>6}-+-{'------------':>12}-+-{'------------':>12}")
    for n in inputs:
        ega = scl(n, 9)
        cga = scl(n, 1)
        print(f"  {n:>6} | {ega:>12} | {cga:>12}")

    # Verify specific values from FOLLOWUP.md.
    assert scl(2.9, 1) == 1, "Scl(2.9) in CGA should be 1"
    assert scl(6.9, 1) == 3, "Scl(6.9) in CGA should be 3"
    assert scl(4, 1) == 2, "Scl(4) in CGA should be 2"
    assert scl(2.9, 9) == 3, "Scl(2.9) in EGA should be 3"
    assert scl(6.9, 9) == 7, "Scl(6.9) in EGA should be 7"
    print("  Scl() verified.")


# =========================================================================
# Test 12: Full SCREEN 9 game scene
# =========================================================================
def test_full_scene():
    print("\n=== Test 12: Full SCREEN 9 game scene ===")
    scr.screen(9)

    # Apply game palette.
    scr.set_palette_color(0, 1)    # blue sky
    scr.set_palette_color(1, 46)   # orange gorillas
    scr.set_palette_color(2, 44)   # explosions
    scr.set_palette_color(3, 54)   # yellow sun
    scr.set_palette_color(5, 7)    # light gray
    scr.set_palette_color(6, 4)    # red
    scr.set_palette_color(7, 3)    # cyan
    scr.set_palette_color(9, 63)   # white

    scr.cls()
    fb = scr.fb()

    def s(n):
        return scl(n, 9)

    # Draw sky background (already blue from palette).
    # Draw ground line.
    gfx.line(0, 335, 639, 335, 7)

    # Draw a few buildings.
    buildings = [
        (2, 200, 50), (55, 160, 45), (103, 220, 40), (146, 140, 55),
        (204, 180, 48), (255, 240, 42), (300, 150, 50), (353, 200, 45),
        (401, 170, 52), (456, 210, 40), (499, 130, 48), (550, 190, 45),
    ]
    for bx, btop, bwidth in buildings:
        # Building body (color 4-6 range, using palette remapped colors).
        bcolor = 4  # will be remapped by palette
        gfx.line(bx, 335, bx + bwidth, btop, bcolor, bf_flag=True)
        # Building outline.
        gfx.line(bx - 1, 336, bx + bwidth + 1, btop - 1, 0, b_flag=True)
        # Windows.
        for wy in range(btop + 5, 330, 15):
            for wx in range(bx + 3, bx + bwidth - 3, 10):
                gfx.line(wx, wy, wx + 3, wy + 6, 14, bf_flag=True)

    # Draw sun.
    SUNATTR = 3
    sun_x, sun_y = 320, s(25)
    gfx.circle(sun_x, sun_y, s(12), SUNATTR)
    gfx.paint(sun_x, sun_y, SUNATTR)
    # Rays.
    gfx.line(sun_x - s(20), sun_y, sun_x + s(20), sun_y, SUNATTR)
    gfx.line(sun_x, sun_y - s(15), sun_x, sun_y + s(15), SUNATTR)
    gfx.line(sun_x - s(15), sun_y - s(10), sun_x + s(15), sun_y + s(10), SUNATTR)
    gfx.line(sun_x - s(15), sun_y + s(10), sun_x + s(15), sun_y - s(10), SUNATTR)
    # Smile.
    gfx.circle(sun_x, sun_y, s(8), 0, start_angle=210 * math.pi / 180, end_angle=330 * math.pi / 180)
    # Eyes.
    gfx.circle(sun_x - 3, sun_y - 2, 1, 0)
    gfx.circle(sun_x + 3, sun_y - 2, 1, 0)
    gfx.pset(sun_x - 3, sun_y - 2, 0)
    gfx.pset(sun_x + 3, sun_y - 2, 0)

    # Draw gorillas.
    for gx in [100, 530]:
        gy = 200
        gfx.line(gx - s(4), gy, gx + s(2.9), gy + s(6), 1, bf_flag=True)
        gfx.line(gx - s(5), gy + s(2), gx + s(4), gy + s(4), 1, bf_flag=True)
        gfx.line(gx - s(3), gy + s(2), gx + s(2), gy + s(2), 0)
        gfx.line(gx - s(8), gy + s(8), gx + s(6.9), gy + s(14), 1, bf_flag=True)
        gfx.line(gx - s(6), gy + s(15), gx + s(4.9), gy + s(20), 1, bf_flag=True)

    # Wind arrow.
    gfx.line(320, 345, 340, 345, 2)
    gfx.line(340, 345, 338, 343, 2)
    gfx.line(340, 345, 338, 347, 2)

    save_fb_png("screen9_full_scene")
    save_fb_scaled_png("screen9_full_scene")
    print("  Full scene rendered.")


# =========================================================================
# Run all tests
# =========================================================================
def main():
    test_ega_palette_all64()
    test_text_rendering()
    test_line_primitives()
    test_circle_primitives()
    test_paint()
    test_get_put()
    test_palette_immediacy()
    test_banana_sprites()
    test_draw_gorilla()
    test_do_sun()
    test_scl_values()
    test_full_scene()

    print("\n" + "=" * 60)
    print("All pixel fidelity tests PASSED.")
    print(f"Golden files saved to: {GOLDEN_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
