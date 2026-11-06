#!/usr/bin/env python3
"""Generate a golden-file game field screenshot from the actual game code.

Run with:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/diag_game_scene.py
"""
import os, sys, math
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame; pygame.init()
import numpy as np

from qb_runtime import screen as scr, text as txt, rng, timing, sound

# Speed up everything.
timing.rest = lambda t: (scr.pump(), scr.present())
timing.sleep = lambda s=0: (scr.pump(), False)[-1]
timing._pump_wait = lambda s: scr.pump()
sound.play = lambda m: None
sound.beep = lambda: None

# Import game module.
sys.argv = ["game.py", "--mute"]
import importlib.util
spec = importlib.util.spec_from_file_location("game", "game.py")
game = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game)

# Initialize.
scr.init(scale=0, fullscreen=False, mute=True, speed=1.0)
timing.set_speed(1.0)
rng.randomize(42)  # Fixed seed for reproducibility.

game.init_vars()
game.set_screen()
scr.cls()

# Capture gorilla sprites (normally done in gorilla_intro).
# Draw offscreen to capture sprites without visible artifacts.
game.draw_gorilla(100, 100, game.ARMSDOWN)
game.draw_gorilla(100, 100, game.LEFTUP)
game.draw_gorilla(100, 100, game.RIGHTUP)
scr.cls()  # Clear the drawn gorillas.

# Build a city and place gorillas.
bcoor = game.make_city_scape()
game.place_gorillas(bcoor)
game.do_sun(game.SUNHAPPY)

# Draw player names and score (as the game would).
txt.locate(1, 1)
txt.print_("Alice")
txt.locate(1, game.MaxCol - 3)
txt.print_("Bob")
game.center(23, "0>Score<0")
scr.present()

# Save framebuffer as golden PNG.
fb = scr.fb()
pal = scr.get_palette()
pal_arr = np.array(pal, dtype=np.uint8)
rgb = pal_arr[fb]
surf = pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))

os.makedirs("tests/golden", exist_ok=True)
pygame.image.save(surf, "tests/golden/game_field.png")
scaled = pygame.transform.scale(surf, (surf.get_width() * 2, surf.get_height() * 2))
pygame.image.save(scaled, "tests/golden/game_field_x2.png")
print(f"Saved game field: {fb.shape[1]}x{fb.shape[0]}")
print(f"  Gorilla 1 at ({game.GorillaX[1]}, {game.GorillaY[1]})")
print(f"  Gorilla 2 at ({game.GorillaX[2]}, {game.GorillaY[2]})")
print(f"  Wind: {game.Wind}")
print(f"  LastBuilding: {game.LastBuilding}")
