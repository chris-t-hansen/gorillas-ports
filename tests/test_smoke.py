"""Headless smoke test for qb_runtime — exercises all modules without a display.

Uses SDL_VIDEODRIVER=dummy and SDL_AUDIODRIVER=dummy so no window or audio
hardware is needed.

Run with:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest tests/test_smoke.py -v
"""

import os
import sys
import unittest

# Force headless drivers before importing pygame.
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestImports(unittest.TestCase):
    """All modules import without error."""

    def test_import_qbmath(self):
        from qb_runtime import qbmath
        self.assertTrue(hasattr(qbmath, "cint"))

    def test_import_format(self):
        from qb_runtime import format as fmt
        self.assertTrue(hasattr(fmt, "qb_str"))

    def test_import_rng(self):
        from qb_runtime import rng
        self.assertTrue(hasattr(rng, "rnd"))

    def test_import_screen(self):
        from qb_runtime import screen
        self.assertTrue(hasattr(screen, "init"))

    def test_import_text(self):
        from qb_runtime import text
        self.assertTrue(hasattr(text, "print_"))

    def test_import_graphics(self):
        from qb_runtime import graphics
        self.assertTrue(hasattr(graphics, "pset"))

    def test_import_keyboard(self):
        from qb_runtime import keyboard
        self.assertTrue(hasattr(keyboard, "inkey"))

    def test_import_timing(self):
        from qb_runtime import timing
        self.assertTrue(hasattr(timing, "timer"))

    def test_import_sound(self):
        from qb_runtime import sound
        self.assertTrue(hasattr(sound, "play"))


class TestQbmathOperations(unittest.TestCase):
    """Verify qbmath works in integration context."""

    def test_cint_bankers_rounding(self):
        from qb_runtime.qbmath import cint
        self.assertEqual(cint(0.5), 0)
        self.assertEqual(cint(1.5), 2)
        self.assertEqual(cint(2.5), 2)
        self.assertEqual(cint(3.5), 4)

    def test_idiv_truncates_toward_zero(self):
        from qb_runtime.qbmath import idiv
        self.assertEqual(idiv(-7, 2), -3)

    def test_mod_sign_of_dividend(self):
        from qb_runtime.qbmath import mod_
        self.assertEqual(mod_(-5, 3), -2)

    def test_sng_precision(self):
        from qb_runtime.qbmath import sng
        result = sng(3.141592653589793)
        self.assertAlmostEqual(result, 3.1415927, places=6)


class TestFormatOperations(unittest.TestCase):
    """Verify format module integration."""

    def test_qb_str_integers(self):
        from qb_runtime.format import qb_str
        self.assertEqual(qb_str(42), " 42")
        self.assertEqual(qb_str(-1), "-1")

    def test_val_parsing(self):
        from qb_runtime.format import val
        self.assertEqual(val("9.8"), 9.8)
        self.assertEqual(val("3"), 3.0)

    def test_string_functions(self):
        from qb_runtime.format import left, right, mid, ucase
        self.assertEqual(left("Player 1", 10), "Player 1")
        self.assertEqual(right("Hello", 3), "llo")
        self.assertEqual(mid("Hello", 2, 3), "ell")
        self.assertEqual(ucase("hello"), "HELLO")


class TestRngOperations(unittest.TestCase):
    """Verify RNG works."""

    def test_rnd_returns_0_to_1(self):
        from qb_runtime.rng import rnd, randomize
        randomize(42)
        for _ in range(100):
            v = rnd(1)
            self.assertGreaterEqual(v, 0.0)
            self.assertLess(v, 1.0)

    def test_fn_ran_range(self):
        from qb_runtime.rng import fn_ran, randomize
        randomize(42)
        for _ in range(100):
            v = fn_ran(6)
            self.assertGreaterEqual(v, 1)
            self.assertLessEqual(v, 6)


class TestTimingOperations(unittest.TestCase):
    """Verify timing module."""

    def test_timer_returns_positive(self):
        from qb_runtime.timing import timer
        t = timer()
        self.assertGreater(t, 0.0)

    def test_timer_increases(self):
        from qb_runtime.timing import timer
        t1 = timer()
        import time
        time.sleep(0.01)
        t2 = timer()
        self.assertGreater(t2, t1)


class TestScreenHeadless(unittest.TestCase):
    """Verify screen module works with dummy SDL driver."""

    @classmethod
    def setUpClass(cls):
        import pygame
        if not pygame.get_init():
            pygame.init()

    def test_screen_modes(self):
        from qb_runtime import screen
        # Test SCREEN 9 (EGA 640x350).
        screen.screen(9)
        self.assertEqual(screen.mode(), 9)
        self.assertEqual(screen.fb_width(), 640)
        self.assertEqual(screen.fb_height(), 350)
        self.assertEqual(screen.cols(), 80)
        self.assertEqual(screen.rows(), 25)

        # Test SCREEN 1 (CGA 320x200).
        screen.screen(1)
        self.assertEqual(screen.mode(), 1)
        self.assertEqual(screen.fb_width(), 320)
        self.assertEqual(screen.fb_height(), 200)
        self.assertEqual(screen.cols(), 40)

        # Test SCREEN 0 (text 640x350).
        screen.screen(0)
        self.assertEqual(screen.mode(), 0)
        self.assertEqual(screen.fb_width(), 640)

    def test_framebuffer_indexed(self):
        from qb_runtime import screen
        import numpy as np
        screen.screen(9)
        fb = screen.fb()
        self.assertEqual(fb.dtype, np.uint8)
        self.assertEqual(fb.shape, (350, 640))

    def test_palette_ega_decode(self):
        from qb_runtime.screen import ega_decode
        # Blue: value 1 → (0, 0, 170)
        self.assertEqual(ega_decode(1), (0, 0, 0xAA))
        # Red: value 4 → (170, 0, 0)
        self.assertEqual(ega_decode(4), (0xAA, 0, 0))
        # Light gray: value 7 → (170, 170, 170)
        self.assertEqual(ega_decode(7), (0xAA, 0xAA, 0xAA))
        # Brown: value 20 → (170, 85, 0)
        self.assertEqual(ega_decode(20), (0xAA, 0x55, 0))
        # Dark gray: value 56 → (85, 85, 85)
        self.assertEqual(ega_decode(56), (0x55, 0x55, 0x55))
        # White: value 63 → (255, 255, 255)
        self.assertEqual(ega_decode(63), (0xFF, 0xFF, 0xFF))

    def test_palette_remap(self):
        from qb_runtime import screen
        screen.screen(9)
        # Simulate SetScreen PALETTE remap.
        screen.set_palette_color(0, 1)   # blue
        screen.set_palette_color(1, 46)  # orange (gorillas)
        screen.set_palette_color(2, 44)  # vivid red/magenta (explosions)
        screen.set_palette_color(3, 54)  # bright green (sun)

        pal = screen.get_palette()
        self.assertEqual(pal[0], (0, 0, 0xAA))        # blue
        self.assertEqual(pal[1], (0xFF, 0xAA, 0x55))   # orange (gorillas)
        self.assertEqual(pal[2], (0xFF, 0x00, 0x55))   # vivid red (EGA 44)
        self.assertEqual(pal[3], (0xFF, 0xFF, 0x00))   # yellow (EGA 54)

    def test_point_and_pset(self):
        from qb_runtime import screen, graphics
        screen.screen(9)
        screen.cls()
        graphics.pset(100, 100, 5)
        self.assertEqual(screen.point(100, 100), 5)
        self.assertEqual(screen.point(0, 0), 0)


class TestGraphicsHeadless(unittest.TestCase):
    """Verify graphics operations on indexed framebuffer."""

    @classmethod
    def setUpClass(cls):
        import pygame
        if not pygame.get_init():
            pygame.init()
        from qb_runtime import screen
        screen.screen(9)

    def test_line(self):
        from qb_runtime import screen, graphics
        screen.cls()
        graphics.line(0, 0, 100, 100, 7)
        # Check that some pixels along the line are set.
        self.assertGreater(screen.point(50, 50), 0)

    def test_line_box(self):
        from qb_runtime import screen, graphics
        screen.cls()
        graphics.line(10, 10, 50, 50, 3, b_flag=True)
        # Corners should be set.
        self.assertEqual(screen.point(10, 10), 3)
        self.assertEqual(screen.point(50, 50), 3)
        # Interior should be empty (B, not BF).
        self.assertEqual(screen.point(30, 30), 0)

    def test_line_filled_box(self):
        from qb_runtime import screen, graphics
        screen.cls()
        graphics.line(10, 10, 50, 50, 4, bf_flag=True)
        # Interior should be filled.
        self.assertEqual(screen.point(30, 30), 4)

    def test_circle(self):
        from qb_runtime import screen, graphics
        screen.cls()
        graphics.circle(100, 100, 30, 7)
        # Some pixel on the circle should be set.
        self.assertEqual(screen.point(130, 100), 7)

    def test_get_put(self):
        from qb_runtime import screen, graphics
        screen.cls()
        # Draw something, capture, erase, restore.
        graphics.pset(50, 50, 5)
        graphics.pset(51, 50, 5)
        sprite = graphics.get_sprite(50, 50, 51, 50)
        self.assertEqual(sprite.shape, (1, 2))
        self.assertEqual(sprite[0, 0], 5)

        # Erase area.
        graphics.line(50, 50, 51, 50, 0)
        self.assertEqual(screen.point(50, 50), 0)

        # Restore with PSET.
        graphics.put_sprite(50, 50, sprite, action="PSET")
        self.assertEqual(screen.point(50, 50), 5)

    def test_put_xor(self):
        from qb_runtime import screen, graphics
        screen.cls()
        graphics.pset(10, 10, 7)
        # XOR with same value → 0.
        import numpy as np
        sprite = np.array([[7]], dtype=np.uint8)
        graphics.put_sprite(10, 10, sprite, action="XOR")
        self.assertEqual(screen.point(10, 10), 0)


class TestTextHeadless(unittest.TestCase):
    """Verify text grid and PRINT operations."""

    @classmethod
    def setUpClass(cls):
        import pygame
        if not pygame.get_init():
            pygame.init()
        from qb_runtime import screen, text
        screen.screen(0)
        text.init()

    def test_print_basic(self):
        from qb_runtime import screen, text
        text.init()
        text.print_("Hello")
        # Check grid: H should be at (0, 0).
        self.assertEqual(int(text._grid_chars[0, 0]), ord("H"))
        self.assertEqual(int(text._grid_chars[0, 4]), ord("o"))

    def test_print_semicolon(self):
        from qb_runtime import text
        text.init()
        text.print_semi("AB")
        text.print_semi("CD")
        # Should be on same line: A B C D.
        self.assertEqual(int(text._grid_chars[0, 0]), ord("A"))
        self.assertEqual(int(text._grid_chars[0, 2]), ord("C"))

    def test_locate(self):
        from qb_runtime import text
        text.init()
        text.locate(5, 10)
        text.print_("X")
        self.assertEqual(int(text._grid_chars[4, 9]), ord("X"))

    def test_color(self):
        from qb_runtime import text
        text.init()
        text.color(14, 1)  # yellow on blue
        self.assertEqual(text._fg, 14)
        self.assertEqual(text._bg, 1)

    def test_view_print(self):
        from qb_runtime import text
        text.init()
        text.view_print(9, 24)
        self.assertEqual(text.get_view_print(), (8, 23))
        text.view_print()  # deactivate
        self.assertEqual(text.get_view_print(), (-1, -1))


class TestSoundParse(unittest.TestCase):
    """Verify PLAY macro parsing (no audio output needed)."""

    def test_parse_simple(self):
        from qb_runtime.sound import _parse_play
        events = _parse_play("O4L4C")
        # Articulation adds a rest after the note, so we get 2 events
        self.assertEqual(len(events), 2)
        freq, dur = events[0]
        self.assertGreater(freq, 0)  # C4 ≈ 261.6 Hz
        self.assertAlmostEqual(freq, 261.6, delta=1.0)
        # Second event should be a rest
        rest_freq, rest_dur = events[1]
        self.assertEqual(rest_freq, 0.0)  # rest

    def test_parse_rest(self):
        from qb_runtime.sound import _parse_play
        events = _parse_play("P4")
        self.assertEqual(len(events), 1)
        freq, dur = events[0]
        self.assertEqual(freq, 0.0)  # rest

    def test_parse_sequence(self):
        from qb_runtime.sound import _parse_play
        events = _parse_play("CDE")
        # Each note produces a note + rest, so 3 notes = 6 events
        self.assertEqual(len(events), 6)

    def test_parse_tempo(self):
        from qb_runtime.sound import _parse_play
        events = _parse_play("T240L4C")
        freq, dur = events[0]
        # T240 → quarter note = 0.25s, MN → 7/8 of that.
        expected = 0.25 * (7 / 8)
        self.assertAlmostEqual(dur, expected, delta=0.01)

    def test_parse_gorilla_intro(self):
        """Parse one of the GorillaIntro PLAY strings."""
        from qb_runtime.sound import _parse_play
        macro = "t120o1l16b9n0baan0bn0bn0baaan0b9n0baan0b"
        events = _parse_play(macro)
        self.assertGreater(len(events), 0)


class TestDecodePutData(unittest.TestCase):
    """Verify banana sprite DATA decoding."""

    def test_decode_ega_banana(self):
        from qb_runtime.graphics import decode_put_data
        # EGA BananaLeft header: 458758 = 0x70006
        # Low word: 0x0006 = 6 (width), high word: 0x0007 = 7 (height).
        header = 0x00070006
        # 8 data longs (32 bytes).
        data = [header] + [0] * 8
        result = decode_put_data(data, bpp=4)
        self.assertEqual(result.shape[0], 7)  # height
        self.assertEqual(result.shape[1], 6)  # width


if __name__ == "__main__":
    unittest.main()
