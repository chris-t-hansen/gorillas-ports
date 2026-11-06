import sys
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()

from qb_runtime import screen as scr, text as txt, graphics as gfx
import game

# Initialize
scr.init(scale=0, fullscreen=False, mute=True, speed=1.0)
game.init_vars()

# Set up a simple game state
game.Mode = 9
game.MaxCol = 80
scr.screen(9)
txt.init()

# Initialize scores
total_wins = [0, 0, 0]  # [unused, player1, player2]

print("Initial scores:", total_wins)
print()

# Scenario 1: Player 1 throws and hits Player 2
print("=== Scenario 1: Player 1 hits Player 2 ===")
tosser = 1
hit = 2  # Player 2 was hit
print(f"tosser={tosser}, hit={hit}")
print(f"hit == tosser? {hit == tosser}")

if hit:
    if hit == tosser:
        other = 3 - tosser
        total_wins[other] = total_wins[other] + 1
        print(f"Thrower hit themselves, opponent (player {other}) scores")
    else:
        total_wins[tosser] = total_wins[tosser] + 1
        print(f"Thrower hit opponent, thrower (player {tosser}) scores")

print(f"Scores after: Player 1 = {total_wins[1]}, Player 2 = {total_wins[2]}")
print(f"Expected: Player 1 = 1, Player 2 = 0")
print()

# Reset
total_wins = [0, 0, 0]

# Scenario 2: Player 2 throws and hits Player 1
print("=== Scenario 2: Player 2 hits Player 1 ===")
tosser = 2
hit = 1  # Player 1 was hit
print(f"tosser={tosser}, hit={hit}")
print(f"hit == tosser? {hit == tosser}")

if hit:
    if hit == tosser:
        other = 3 - tosser
        total_wins[other] = total_wins[other] + 1
        print(f"Thrower hit themselves, opponent (player {other}) scores")
    else:
        total_wins[tosser] = total_wins[tosser] + 1
        print(f"Thrower hit opponent, thrower (player {tosser}) scores")

print(f"Scores after: Player 1 = {total_wins[1]}, Player 2 = {total_wins[2]}")
print(f"Expected: Player 1 = 0, Player 2 = 1")
print()

# Scenario 3: Player 1 throws and hits themselves (low velocity)
print("=== Scenario 3: Player 1 hits themselves ===")
total_wins = [0, 0, 0]
tosser = 1
hit = 1  # Player 1 was hit (themselves)
print(f"tosser={tosser}, hit={hit}")
print(f"hit == tosser? {hit == tosser}")

if hit:
    if hit == tosser:
        other = 3 - tosser
        total_wins[other] = total_wins[other] + 1
        print(f"Thrower hit themselves, opponent (player {other}) scores")
    else:
        total_wins[tosser] = total_wins[tosser] + 1
        print(f"Thrower hit opponent, thrower (player {tosser}) scores")

print(f"Scores after: Player 1 = {total_wins[1]}, Player 2 = {total_wins[2]}")
print(f"Expected: Player 1 = 0, Player 2 = 1")
