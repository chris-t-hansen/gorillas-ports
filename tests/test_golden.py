"""Golden-file tests — verify framebuffer output matches reference PNGs.

Compares rendered framebuffer PNGs against golden files in tests/golden/.
Any pixel difference > 0 causes a failure (pixel-exact matching).

Run with:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m unittest tests/test_golden -v

If golden files don't exist yet, run the diagnostic first:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/diag_pixel_fidelity.py
"""

import os
import sys
import math
import unittest
import numpy as np

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

pygame.init()

from qb_runtime import screen as scr
from qb_runtime import text as txt
from qb_runtime import graphics as gfx
from qb_runtime import sound
from qb_runtime.graphics import decode_put_data

GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")


def _scl(n: float, mode: int) -> int:
    """Game-level Scl() function."""
    if n != int(n):
        if mode == 1:
            n = n - 1
    if mode == 1:
        return round(n / 2 + 0.1)
    else:
        return round(n)


def _fb_to_rgb():
    """Convert current indexed framebuffer to RGB numpy array."""
    fb = scr.fb()
    pal = scr.get_palette()
    pal_arr = np.array(pal, dtype=np.uint8)
    return pal_arr[fb]


def _load_golden_png(name: str) -> np.ndarray:
    """Load a golden PNG and return as RGB numpy array (H, W, 3)."""
    path = os.path.join(GOLDEN_DIR, f"{name}.png")
    if not os.path.exists(path):
        return None
    surf = pygame.image.load(path)
    return pygame.surfarray.array3d(surf).transpose(1, 0, 2)


def _save_current_fb(name: str):
    """Save current framebuffer to golden directory."""
    rgb = _fb_to_rgb()
    surf = pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))
    path = os.path.join(GOLDEN_DIR, f"{name}.png")
    pygame.image.save(surf, path)


def _compare_rgb(actual: np.ndarray, expected: np.ndarray) -> tuple:
    """Compare two RGB arrays. Returns (match: bool, diff_count: int, diff_pct: float)."""
    if actual.shape != expected.shape:
        return False, -1, -1.0
    diff = np.any(actual != expected, axis=2)
    diff_count = int(np.sum(diff))
    total = actual.shape[0] * actual.shape[1]
    return diff_count == 0, diff_count, diff_count / total * 100


def _setup_screen9_palette():
    """Apply the game's SetScreen palette remap for SCREEN 9."""
    scr.set_palette_color(0, 1)
    scr.set_palette_color(1, 46)
    scr.set_palette_color(2, 44)
    scr.set_palette_color(3, 54)
    scr.set_palette_color(5, 7)
    scr.set_palette_color(6, 4)
    scr.set_palette_color(7, 3)
    scr.set_palette_color(9, 63)


class TestGoldenFiles(unittest.TestCase):
    """Verify rendered scenes match golden file references."""

    def test_ega_64color_swatch(self):
        """EGA 64-color palette swatch."""
        from qb_runtime.screen import ega_decode

        swatch = np.zeros((8 * 16, 8 * 16, 3), dtype=np.uint8)
        for v in range(64):
            r, g, b = ega_decode(v)
            row = (v // 8) * 16
            col = (v % 8) * 16
            swatch[row : row + 16, col : col + 16] = (r, g, b)

        golden = _load_golden_png("ega_64colors")
        if golden is None:
            self.skipTest("Golden file not found — run diag_pixel_fidelity.py first")
        match, diff_count, pct = _compare_rgb(swatch, golden)
        self.assertTrue(match, f"EGA swatch: {diff_count} pixels differ ({pct:.1f}%)")

    def test_screen0_text(self):
        """SCREEN 0 text rendering."""
        scr.screen(0)
        txt.init()
        txt.color(15, 0)
        txt.locate(1, 1)
        txt.print_("GORILLAS")
        txt.locate(3, 1)
        txt.color(7, 0)
        txt.print_("Copyright (C) Microsoft Corporation 1990")
        txt.locate(5, 1)
        txt.color(14, 0)
        txt.print_("Your mission is to hit your opponent")
        txt.locate(6, 1)
        txt.print_("with the exploding banana.")
        txt.locate(8, 1)
        txt.color(7, 0)
        txt.print_("Zone1", sep=",")
        txt.print_("Zone2", sep=",")
        txt.print_("Zone3")
        txt.locate(10, 1)
        txt.print_semi("Score: ")
        txt.color(15, 0)
        txt.print_("42")
        txt.locate(12, 1)
        txt.color(7, 0)
        for code in [1, 2, 3, 4, 5, 6]:
            txt._write_char(code)
        txt._write_char(32)
        for code in range(176, 180):
            txt._write_char(code)
        txt._write_char(32)
        for code in range(219, 224):
            txt._write_char(code)
        txt._advance_newline()

        golden = _load_golden_png("screen0_text")
        if golden is None:
            self.skipTest("Golden file not found")
        rgb = _fb_to_rgb()
        match, diff_count, pct = _compare_rgb(rgb, golden)
        self.assertTrue(match, f"SCREEN 0 text: {diff_count} pixels differ ({pct:.1f}%)")

    def test_screen9_banana_sprites(self):
        """EGA banana sprites decoded from DATA and PUT on screen."""
        scr.screen(9)
        _setup_screen9_palette()
        scr.cls()

        EGA_BANANAS = {
            "left":  [458758, 202116096, 471604224, 943208448, 943208448, 943208448, 471604224, 202116096, 0],
            "down":  [262153, -2134835200, -2134802239, -2130771968, -2130738945, 8323072, 8323199, 4063232, 4063294],
            "up":    [262153, 4063232, 4063294, 8323072, 8323199, -2130771968, -2130738945, -2134835200, -2134802239],
            "right": [458758, -1061109760, -522133504, 1886416896, 1886416896, 1886416896, -522133504, -1061109760, 0],
        }

        def _to_u32(longs):
            return [v & 0xFFFFFFFF for v in longs]
        positions = {"left": (50, 50), "up": (100, 50), "down": (150, 50), "right": (200, 50)}

        for name, longs in EGA_BANANAS.items():
            sprite = decode_put_data(_to_u32(longs), bpp=4)
            x, y = positions[name]
            gfx.put_sprite(x, y, sprite, action="PSET")

        golden = _load_golden_png("screen9_bananas")
        if golden is None:
            self.skipTest("Golden file not found")
        rgb = _fb_to_rgb()
        match, diff_count, pct = _compare_rgb(rgb, golden)
        self.assertTrue(match, f"Banana sprites: {diff_count} pixels differ ({pct:.1f}%)")

    def test_screen9_sun(self):
        """Sun drawing (happy face)."""
        scr.screen(9)
        scr.set_palette_color(0, 1)
        scr.set_palette_color(3, 54)
        scr.cls()

        def s(n):
            return _scl(n, 9)

        SUNATTR = 3
        pi = math.pi
        x = 320
        y = s(25)

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
        gfx.circle(x, y, s(8), 0, start_angle=210 * pi / 180, end_angle=330 * pi / 180)
        gfx.circle(x - 3, y - 2, 1, 0)
        gfx.circle(x + 3, y - 2, 1, 0)
        gfx.pset(x - 3, y - 2, 0)
        gfx.pset(x + 3, y - 2, 0)

        golden = _load_golden_png("screen9_sun_happy")
        if golden is None:
            self.skipTest("Golden file not found")
        rgb = _fb_to_rgb()
        match, diff_count, pct = _compare_rgb(rgb, golden)
        self.assertTrue(match, f"Sun (happy): {diff_count} pixels differ ({pct:.1f}%)")

    def test_palette_immediacy(self):
        """Verify PALETTE changes affect already-drawn pixels at present time."""
        scr.screen(9)
        scr.cls()
        gfx.line(50, 50, 150, 120, 5, bf_flag=True)

        # Palette before change: register 5 = default (magenta).
        pal_before = scr.get_palette()

        scr.set_palette_color(5, 63)  # change to white.
        pal_after = scr.get_palette()

        # Framebuffer value unchanged.
        self.assertEqual(scr.point(100, 85), 5)
        # But RGB mapping changed.
        self.assertNotEqual(pal_before[5], pal_after[5])
        self.assertEqual(pal_after[5], (255, 255, 255))


class TestLineFidelity(unittest.TestCase):
    """Verify LINE primitive correctness after the Bresenham fix."""

    @classmethod
    def setUpClass(cls):
        scr.screen(9)

    def test_horizontal_line(self):
        scr.cls()
        gfx.line(10, 50, 100, 50, 15)
        for x in range(10, 101):
            self.assertEqual(scr.point(x, 50), 15, f"Missing pixel at ({x}, 50)")

    def test_vertical_line(self):
        scr.cls()
        gfx.line(50, 10, 50, 100, 15)
        for y in range(10, 101):
            self.assertEqual(scr.point(50, y), 15, f"Missing pixel at (50, {y})")

    def test_diagonal_line(self):
        scr.cls()
        gfx.line(0, 0, 50, 50, 15)
        for i in range(51):
            self.assertEqual(scr.point(i, i), 15, f"Missing pixel at ({i}, {i})")

    def test_box_all_edges(self):
        scr.cls()
        gfx.line(20, 20, 80, 60, 15, b_flag=True)
        # Top edge.
        for x in range(20, 81):
            self.assertEqual(scr.point(x, 20), 15, f"Top edge missing at ({x}, 20)")
        # Bottom edge.
        for x in range(20, 81):
            self.assertEqual(scr.point(x, 60), 15, f"Bottom edge missing at ({x}, 60)")
        # Left edge.
        for y in range(20, 61):
            self.assertEqual(scr.point(20, y), 15, f"Left edge missing at (20, {y})")
        # Right edge.
        for y in range(20, 61):
            self.assertEqual(scr.point(80, y), 15, f"Right edge missing at (80, {y})")

    def test_filled_box(self):
        scr.cls()
        gfx.line(10, 10, 30, 30, 7, bf_flag=True)
        for y in range(10, 31):
            for x in range(10, 31):
                self.assertEqual(scr.point(x, y), 7, f"Fill missing at ({x}, {y})")


class TestPaintFidelity(unittest.TestCase):
    """Verify PAINT flood fill correctness."""

    @classmethod
    def setUpClass(cls):
        scr.screen(9)

    def test_fill_box(self):
        scr.cls()
        gfx.line(10, 10, 50, 40, 3, b_flag=True)  # border is 3
        gfx.paint(25, 25, 3)  # fill with 3, border defaults to 3
        # Interior filled.
        self.assertEqual(scr.point(25, 25), 3)
        self.assertEqual(scr.point(11, 11), 3)
        self.assertEqual(scr.point(49, 39), 3)
        # Exterior untouched.
        self.assertEqual(scr.point(5, 5), 0)
        self.assertEqual(scr.point(55, 45), 0)
        # Border intact.
        self.assertEqual(scr.point(10, 10), 3)
        self.assertEqual(scr.point(50, 40), 3)

    def test_fill_circle(self):
        scr.cls()
        gfx.circle(100, 100, 20, 5)  # border is 5
        gfx.paint(100, 100, 5)  # fill with 5, border defaults to 5
        self.assertEqual(scr.point(100, 100), 5)
        self.assertEqual(scr.point(100, 85), 5)
        # Exterior untouched.
        self.assertEqual(scr.point(10, 10), 0)

    def test_paint_default_border(self):
        """PAINT border defaults to fill color, not foreground."""
        scr.cls()
        # Draw a box with color 15 (white)
        gfx.line(10, 10, 50, 50, 15, b_flag=True)
        # PAINT with fill=3 — border defaults to 3 (same as fill)
        # Since box border is 15, not 3, paint will leak out
        gfx.paint(30, 30, 3)
        # Paint should have filled the entire screen (leaked out)
        self.assertEqual(scr.point(5, 5), 3)
        
        # Now test correct usage: border matches outline
        scr.cls()
        gfx.line(10, 10, 50, 50, 3, b_flag=True)  # border is 3
        gfx.paint(30, 30, 3)  # fill=3, border=3 (default)
        # Paint should stay inside
        self.assertEqual(scr.point(30, 30), 3)
        self.assertEqual(scr.point(5, 5), 0)


if __name__ == "__main__":
    unittest.main()
