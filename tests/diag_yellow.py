#!/usr/bin/env python3
"""Diagnostic: capture framebuffer state at the moment play_game presents its first frame."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame; pygame.init()
import numpy as np

from qb_runtime import screen as scr, text as txt, rng, timing, sound, keyboard as kbd

# Speed up
timing.rest = lambda t: (scr.pump(), scr.present())
timing.sleep = lambda s=0: (scr.pump(), False)[-1]
timing._pump_wait = lambda s: scr.pump()
sound.play = lambda m: None
sound.beep = lambda: None

# Script keys to get through intro/inputs/gorilla_intro
script = [
    chr(13),  # dismiss SparklePause
    "A","l","i","c","e", chr(13),  # Player 1
    "B","o","b", chr(13),          # Player 2
    "1", chr(13),                   # 1 game
    chr(13),                         # default gravity
    "P",                             # skip dance
]
idx = 0
def fake_inkey():
    global idx
    scr.pump()
    if idx < len(script):
        k = script[idx]; idx += 1; return k
    return ""
def fake_flush(): pass
kbd.inkey = fake_inkey
kbd.flush = fake_flush

sys.argv = ["game.py", "--mute"]
import importlib.util
spec = importlib.util.spec_from_file_location("game", "game.py")
game = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game)

# Run through setup
scr.init(scale=0, fullscreen=False, mute=True, speed=1.0)
timing.set_speed(1.0)
rng.randomize(42)

game.init_vars()
game.intro()
name1, name2, num_games = game.get_inputs()
game.gorilla_intro(name1, name2)

# Now simulate what play_game does for the first frame
print("=== Entering play_game first frame ===")
print(f"Mode = {game.Mode}")

scr.screen(game.Mode)
txt.init()
game.set_screen()

print(f"After set_screen, palette:")
pal = scr.get_palette()
for i, c in enumerate(pal):
    print(f"  [{i}] = {c}")

scr.cls()
print(f"After cls, fb unique values: {sorted(set(scr.fb().flatten().tolist()))}")

rng.randomize(42)
bcoor = game.make_city_scape()
print(f"After make_city_scape, fb unique values: {sorted(set(scr.fb().flatten().tolist()))}")

game.place_gorillas(bcoor)
print(f"After place_gorillas, fb unique values: {sorted(set(scr.fb().flatten().tolist()))}")

game.do_sun(game.SUNHAPPY)
print(f"After do_sun, fb unique values: {sorted(set(scr.fb().flatten().tolist()))}")

# Count pixels of each value
fb = scr.fb()
for v in sorted(set(fb.flatten().tolist())):
    count = np.sum(fb == v)
    pct = count / fb.size * 100
    rgb = pal[v]
    print(f"  value {v:2d} (RGB{rgb}): {count:6d} pixels ({pct:.1f}%)")

# Save
pal_arr = np.array(pal, dtype=np.uint8)
rgb = pal_arr[fb]
surf = pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))
pygame.image.save(surf, "tests/output_diag_yellow.png")
print(f"\nSaved diagnostic: tests/output_diag_yellow.png")

# Also save raw fb values as grayscale
gray = (fb * 16).astype(np.uint8)
gray_surf = pygame.Surface((fb.shape[1], fb.shape[0]))
pygame.surfarray.blit_array(gray_surf, gray.T)
pygame.image.save(gray_surf, "tests/output_diag_yellow_raw.png")
print(f"Saved raw fb: tests/output_diag_yellow_raw.png")
