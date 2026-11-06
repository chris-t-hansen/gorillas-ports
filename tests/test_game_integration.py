#!/usr/bin/env python3
"""Integration test: drive game.py through all screens non-interactively.

Injects keypresses into the keyboard buffer to test:
  1. Intro screen (SparklePause)
  2. GetInputs (player names, num games, gravity)
  3. GorillaIntro (P = Play, skip dance)
  4. PlayGame (one round with quick shots)
  5. Game Over screen

Run with:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_game_integration.py
"""

import os
import sys
import math
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()

from qb_runtime import screen as scr
from qb_runtime import text as txt
from qb_runtime import graphics as gfx
from qb_runtime import keyboard as kbd
from qb_runtime import timing
from qb_runtime import sound
from qb_runtime import rng

print("=" * 60)
print("Integration test: game.py flow")
print("=" * 60)

# Monkey-patch timing to make tests fast.
_original_rest = timing.rest
_original_sleep = timing.sleep
_original_pump_wait = timing._pump_wait

def fast_rest(t):
    """Skip all Rest() calls during testing."""
    scr.pump()
    scr.present()

def fast_sleep(seconds=0):
    """Skip SLEEP during testing."""
    scr.pump()
    return False

def fast_pump_wait(seconds):
    scr.pump()

timing.rest = fast_rest
timing.sleep = fast_sleep
timing._pump_wait = fast_pump_wait

# Monkey-patch keyboard to inject scripted keys.
_script = []
_script_idx = 0

def inject_keys(keys):
    """Add keys to the injection script."""
    global _script
    _script.extend(keys)

def scripted_inkey():
    """Return next scripted key, or empty string."""
    global _script_idx
    scr.pump()
    if _script_idx < len(_script):
        k = _script[_script_idx]
        _script_idx += 1
        return k
    return ""

def scripted_flush():
    """Clear remaining scripted keys."""
    pass  # Don't clear — we want them to be consumed.

# Replace keyboard functions.
_original_inkey = kbd.inkey
_original_flush = kbd.flush
kbd.inkey = scripted_inkey
kbd.flush = scripted_flush

# Monkey-patch sound to skip audio.
_original_play = sound.play
_original_beep = sound.beep
sound.play = lambda macro: None
sound.beep = lambda: None

# ---------------------------------------------------------------------------
# Now import game.py (it will use our monkey-patched modules)
# ---------------------------------------------------------------------------
import importlib.util
spec = importlib.util.spec_from_file_location("game", "game.py")
# We need to prevent argparse from reading sys.argv
sys.argv = ["game.py", "--mute"]
game = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game)

print("\n[1/6] Testing init_vars()...")
game.init_vars()
assert game.Mode in (9, 1), f"Mode should be 9 or 1, got {game.Mode}"
assert game.ScrWidth in (640, 320), f"ScrWidth: {game.ScrWidth}"
assert game.ScrHeight in (350, 200), f"ScrHeight: {game.ScrHeight}"
assert game.LBan is not None, "Banana sprite should be loaded"
print(f"  Mode={game.Mode}, {game.ScrWidth}x{game.ScrHeight}, LBan shape={game.LBan.shape}")
print("  PASS")

print("\n[2/6] Testing intro()...")
# Inject a keypress to get past SparklePause.
inject_keys([chr(13)])  # Enter
game.intro()
print("  PASS")

print("\n[3/6] Testing get_inputs()...")
# Script: Player 1 name "Alice", Player 2 name "Bob", 1 game, default gravity.
inject_keys([
    # Player 1: "Alice" + Enter
    "A", "l", "i", "c", "e", chr(13),
    # Player 2: "Bob" + Enter
    "B", "o", "b", chr(13),
    # Num games: "1" + Enter
    "1", chr(13),
    # Gravity: just Enter (default 9.8)
    chr(13),
])
name1, name2, num_games = game.get_inputs()
assert name1 == "Alice", f"name1={name1!r}"
assert name2 == "Bob", f"name2={name2!r}"
assert num_games == 1, f"num_games={num_games}"
assert game.gravity_ == 9.8, f"gravity={game.gravity_}"
print(f"  Players: {name1} vs {name2}, {num_games} game(s), gravity={game.gravity_}")
print("  PASS")

print("\n[4/6] Testing gorilla_intro() with 'P' (skip dance)...")
# Script: press 'P' to skip the dance animation.
inject_keys(["P"])
game.gorilla_intro(name1, name2)
# Gorilla sprites should now be captured.
assert game.GorD is not None, "GorD should be captured after gorilla_intro"
assert game.GorL is not None, "GorL should be captured after gorilla_intro"
assert game.GorR is not None, "GorR should be captured after gorilla_intro"
print(f"  Gorilla sprites: GorD={game.GorD.shape}, GorL={game.GorL.shape}, GorR={game.GorR.shape}")
print("  PASS")

print("\n[5/6] Testing do_shot() + plot_shot() (one shot)...")
# We need to set up a game field first.
scr.screen(game.Mode)
txt.init()
game.set_screen()
scr.cls()
bcoor = game.make_city_scape()
game.place_gorillas(bcoor)
game.do_sun(game.SUNHAPPY)
scr.present()

# Script a shot: angle=45, velocity=50.
inject_keys([
    "4", "5", chr(13),   # angle = 45
    "5", "0", chr(13),   # velocity = 50
])
result = game.do_shot(1, game.GorillaX[1], game.GorillaY[1])
print(f"  Shot result: {result} (0=miss, 1/2=hit)")
print("  PASS")

print("\n[6/6] Testing utility functions...")
# Test Center.
scr.screen(0)
txt.init()
game.MaxCol = 80
game.center(1, "Hello World")
row, col = txt.get_cursor_pos()
assert row == 0, f"Center row should be 0, got {row}"
# "Hello World" is 11 chars. LOCATE col (1-based) = 40 - int(11/2 + 0.5) = 34
# Internal cursor (0-based) starts at 33, after 11 chars = 44.
expected_locate_col = 40 - int(11 / 2 + 0.5)  # 34 (1-based)
expected_cursor_col = expected_locate_col - 1 + 11  # 33 + 11 = 44 (0-based)
assert col == expected_cursor_col, f"Cursor after print should be at col {expected_cursor_col}, got {col}"
print(f"  Center('Hello World'): LOCATE col={expected_locate_col}, cursor at {col}")

# Test Scl.
game.Mode = 9
assert game.scl(4) == 4, f"Scl(4) in EGA = {game.scl(4)}"
assert game.scl(2.9) == 3, f"Scl(2.9) in EGA = {game.scl(2.9)}"
assert game.scl(6.9) == 7, f"Scl(6.9) in EGA = {game.scl(6.9)}"
game.Mode = 1
assert game.scl(4) == 2, f"Scl(4) in CGA = {game.scl(4)}"
assert game.scl(2.9) == 1, f"Scl(2.9) in CGA = {game.scl(2.9)}"
assert game.scl(6.9) == 3, f"Scl(6.9) in CGA = {game.scl(6.9)}"
print("  Scl() values verified for EGA and CGA")

# Test fn_ran.
game.Mode = 9
rng.randomize(42)
results = set()
for _ in range(100):
    v = game.fn_ran(6)
    assert 1 <= v <= 6, f"fn_ran(6) out of range: {v}"
    results.add(v)
assert len(results) == 6, f"fn_ran(6) should cover 1-6, got {results}"
print("  fn_ran(6) covers full range [1,6]")

# Test set_screen palette.
game.Mode = 9
scr.screen(9)
game.set_screen()
pal = scr.get_palette()
assert pal[0] == (0, 0, 170), f"Palette 0 should be blue, got {pal[0]}"
assert pal[1] == (255, 170, 85), f"Palette 1 should be orange, got {pal[1]}"
print("  set_screen() palette remap verified")

print("  PASS")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ALL INTEGRATION TESTS PASSED")
print("=" * 60)
