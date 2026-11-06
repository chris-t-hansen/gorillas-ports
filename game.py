#!/usr/bin/env python3
"""Gorillas — faithful Python port of QBASIC GORILLA.BAS (1990).

Copyright (C) Microsoft Corporation 1990 (original).
This port preserves all behavior, quirks, and bugs of the original.

Usage:
    python game.py [--scale N] [--fullscreen] [--mute] [--speed X]

Controls:
    Enter       Confirm input
    Esc         (reserved)
    Arrow keys  Navigate (where applicable)
    V / P       View intro / Play game (GorillaIntro choice)
    0-9, .      Numeric input (angle, velocity)

See QUIRKS.md for preserved bugs and TIMING_NOTES.md for delay conversions.
"""

import argparse
import math
import sys
import os

# ---------------------------------------------------------------------------
# Parse CLI arguments early (before pygame init)
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Gorillas — QBASIC GORILLA.BAS faithful port"
    )
    parser.add_argument(
        "--scale", type=int, default=0,
        help="Integer scale factor (0 = auto-fit to display)"
    )
    parser.add_argument(
        "--fullscreen", action="store_true",
        help="Start in fullscreen mode"
    )
    parser.add_argument(
        "--mute", action="store_true",
        help="Disable sound"
    )
    parser.add_argument(
        "--speed", type=float, default=1.0,
        help="Speed multiplier for game timing (default: 1.0)"
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Initialize runtime
# ---------------------------------------------------------------------------

args = parse_args()

from qb_runtime import screen as scr
from qb_runtime import text as txt
from qb_runtime import graphics as gfx
from qb_runtime import keyboard as kbd
from qb_runtime import timing
from qb_runtime import sound
from qb_runtime import rng
from qb_runtime.qbmath import cint, sng
from qb_runtime.format import (
    left, right, mid, instr, space, string_, ucase, lcase,
    ltrim, rtrim, val, qb_str, chr_, asc,
)


# ---------------------------------------------------------------------------
# Constants (BAS L60-71)
# ---------------------------------------------------------------------------
SPEEDCONST = 500
TRUE = -1
FALSE = 0  # NOT TRUE in QBASIC is 0 (since TRUE=-1, NOT -1 = 0)
HITSELF = 1
BACKATTR = 0
OBJECTCOLOR = 1
WINDOWCOLOR = 14
SUNATTR = 3
SUNHAPPY = FALSE
SUNSHOCK = TRUE
RIGHTUP = 1
LEFTUP = 2
ARMSDOWN = 3

# ---------------------------------------------------------------------------
# TYPE XYPoint (BAS L55-58)
# ---------------------------------------------------------------------------
class XYPoint:
    __slots__ = ("xcoor", "ycoor")
    def __init__(self, x=0, y=0):
        self.xcoor = x
        self.ycoor = y


# ---------------------------------------------------------------------------
# Global variables (BAS L73-99)
# ---------------------------------------------------------------------------
GorillaX = [0, 0, 0]  # 1-indexed: GorillaX(1), GorillaX(2)
GorillaY = [0, 0, 0]
LastBuilding = 0

pi_ = 4.0 * math.atan(1.0)  # pi# = 4 * ATN(1#)  (BAS L144)

LBan = []  # Banana sprites (numpy arrays)
RBan = []
UBan = []
DBan = []
GorD = None  # Gorilla sprites (numpy arrays)
GorL = None
GorR = None

gravity_ = 0.0  # gravity#
Wind = 0

ScrHeight = 0
ScrWidth = 0
Mode = 0
MaxCol = 0

ExplosionColor = 0
SunColor = 0
BackColor = 0
SunHit = 0

SunHt = 0
GHeight = 0
MachSpeed = float(SPEEDCONST)


# ---------------------------------------------------------------------------
# DEF FnRan(x) = INT(RND(1) * x) + 1  (BAS L110)
# ---------------------------------------------------------------------------
def fn_ran(x: int) -> int:
    return int(rng.rnd(1) * x) + 1


# ---------------------------------------------------------------------------
# Scl(n!) — BAS L1036-1049
# ---------------------------------------------------------------------------
def scl(n: float) -> int:
    """Scale factor for CGA vs EGA. Game-level function (not runtime)."""
    if n != int(n):
        if Mode == 1:
            n = n - 1
    if Mode == 1:
        return cint(n / 2 + 0.1)
    else:
        return cint(n)


# ---------------------------------------------------------------------------
# Center(Row, Text$) — BAS L242-248
# ---------------------------------------------------------------------------
def center(row: int, text: str) -> None:
    """Center and print text on given row. BAS L242-248."""
    col = MaxCol // 2
    # LOCATE Row, Col - (LEN(Text$)/2 + .5)
    # QBASIC LOCATE truncates, so int() of the float expression.
    loc_col = col - int(len(text) / 2 + 0.5)
    if loc_col < 1:
        loc_col = 1
    txt.locate(row, loc_col)
    txt.print_semi(text)


# ---------------------------------------------------------------------------
# CalcDelay! — BAS L228-236
# ---------------------------------------------------------------------------
def calc_delay() -> float:
    """CalcDelay! — returns MachSpeed value.
    In the port, we use SPEEDCONST as nominal (no calibration needed)."""
    return float(SPEEDCONST)


# ---------------------------------------------------------------------------
# Rest(t#) — BAS L1024-1031
# ---------------------------------------------------------------------------
def rest(t: float) -> None:
    """Rest(t#) — pause for t# seconds (scaled by speed multiplier)."""
    timing.rest(t)


# ---------------------------------------------------------------------------
# SetScreen — BAS L1051-1073
# ---------------------------------------------------------------------------
def set_screen() -> None:
    global ExplosionColor, BackColor
    if Mode == 9:
        ExplosionColor = 2
        BackColor = 1
        scr.set_palette_color(0, 1)
        scr.set_palette_color(1, 46)
        scr.set_palette_color(2, 44)
        scr.set_palette_color(3, 54)
        scr.set_palette_color(5, 7)
        scr.set_palette_color(6, 4)
        scr.set_palette_color(7, 3)
        scr.set_palette_color(9, 63)
    else:
        ExplosionColor = 2
        BackColor = 0
        # COLOR 0, 2 in SCREEN 1 — black bg, palette 1
        # (CGA palette handling is a TODO for CGA path)


# ---------------------------------------------------------------------------
# SparklePause — BAS L1075-1110
# ---------------------------------------------------------------------------
def sparkle_pause() -> None:
    """Creates flashing border for intro and game over screens."""
    txt.color(4, 0)
    a_str = "*    *    *    *    *    *    *    *    *    *    *    *    *    *    *    *    *    "

    kbd.flush()

    while kbd.inkey() == "":
        for a in range(1, 6):  # FOR A = 1 TO 5
            # Top row sparkle
            txt.locate(1, 1)
            txt.print_semi(mid(a_str, a, MaxCol))
            # Bottom row sparkle
            txt.locate(25, 1)
            txt.print_semi(mid(a_str, a, MaxCol))
            # Left column sparkle
            for i in range(2, 25):  # rows 2-24
                txt.locate(i, 1)
                if (i + a) % 5 == 0:
                    txt.print_semi("*")
                else:
                    txt.print_semi(" ")
                # Right column sparkle
                txt.locate(i, MaxCol)
                if (i + a) % 5 == 0:
                    txt.print_semi("*")
                else:
                    txt.print_semi(" ")
            scr.present()
            timing._pump_wait(0.05)  # ~20 fps sparkle

    kbd.flush()


# ---------------------------------------------------------------------------
# Intro — BAS L663-686
# ---------------------------------------------------------------------------
def intro() -> None:
    """Display game introduction. BAS L663-686."""
    global MaxCol

    scr.screen(0)
    # WIDTH 80, 25
    MaxCol = 80
    txt.init()

    txt.color(15, 0)
    txt.cls()

    center(4, "Q B a s i c    G O R I L L A S")
    txt.color(7, 0)
    center(6, "Copyright (C) Microsoft Corporation 1990")
    center(8, "Your mission is to hit your opponent with the exploding")
    center(9, "banana by varying the angle and power of your throw, taking")
    center(10, "into account wind speed, gravity, and the city skyline.")
    center(11, "The wind speed is shown by a directional arrow at the bottom")
    center(12, "of the playing field, its length relative to its strength.")
    center(24, "Press any key to continue")

    sound.play("MBT160O1L8CDEDCDL4ECC")
    sparkle_pause()

    if Mode == 1:
        MaxCol = 40


# ---------------------------------------------------------------------------
# GetInputs — BAS L492-530
# ---------------------------------------------------------------------------
def get_inputs() -> tuple:
    """Get player names, number of games, gravity. Returns (name1, name2, num_games)."""
    txt.color(7, 0)
    txt.cls()

    txt.locate(8, 15)
    player1 = kbd.line_input("Name of Player 1 (Default = 'Player 1'): ")
    if player1 == "":
        player1 = "Player 1"
    else:
        player1 = left(player1, 10)

    txt.locate(10, 15)
    player2 = kbd.line_input("Name of Player 2 (Default = 'Player 2'): ")
    if player2 == "":
        player2 = "Player 2"
    else:
        player2 = left(player2, 10)

    # Play to how many points
    num_games = 0
    while True:
        txt.locate(12, 56)
        txt.print_semi(space(25))
        txt.locate(12, 13)
        game_str = kbd.input_str("Play to how many total points (Default = 3)")
        num_games = int(val(left(game_str, 2)))
        if (num_games > 0 and len(game_str) < 3) or len(game_str) == 0:
            break
    if num_games == 0:
        num_games = 3

    # Gravity
    global gravity_
    while True:
        txt.locate(14, 53)
        txt.print_semi(space(28))
        txt.locate(14, 17)
        grav_str = kbd.input_str("Gravity in Meters/Sec (Earth = 9.8)")
        gravity_ = val(grav_str)
        if gravity_ > 0 or len(grav_str) == 0:
            break
    if gravity_ == 0:
        gravity_ = 9.8

    return player1, player2, num_games


# ---------------------------------------------------------------------------
# GetNum#(Row, Col) — BAS L532-577
# ---------------------------------------------------------------------------
def get_num(row: int, col: int) -> float:
    """GetNum# — INKEY$-based numeric entry. BAS L532-577."""
    result = ""
    done = False

    kbd.flush()

    while not done:
        txt.locate(row, col)
        txt.print_semi(result + chr_(95) + "    ")  # underscore cursor + padding
        scr.present()

        k = kbd.inkey()
        if not k:
            import pygame
            pygame.time.wait(10)
            continue

        if k >= "0" and k <= "9":
            result = result + k
        elif k == ".":
            if instr(1, result, ".") == 0:
                result = result + k
        elif k == chr_(13):  # Enter
            if val(result) > 360:
                result = ""
            else:
                done = True
        elif k == chr_(8):  # Backspace
            if len(result) > 0:
                result = left(result, len(result) - 1)
        else:
            if len(k) > 0:
                sound.beep()

    txt.locate(row, col)
    txt.print_semi(result + " ")
    scr.present()

    return val(result)


# ---------------------------------------------------------------------------
# DoShot — BAS L278-326
# ---------------------------------------------------------------------------
def do_shot(player_num: int, x: int, y: int) -> int:
    """DoShot — get angle/velocity and plot shot. BAS L278-326.
    Returns: player number hit (0 = miss, 1 or 2 = hit, HITSELF=1 if self-hit)."""

    txt.color(7, 0)

    # Position input based on player number
    if player_num == 1:
        locate_col = 1
    else:
        locate_col = 66 if Mode == 9 else 26

    txt.locate(2, locate_col)
    txt.print_semi("Angle:")
    scr.present()
    angle = get_num(2, locate_col + 7)

    txt.locate(3, locate_col)
    txt.print_semi("Velocity:")
    scr.present()
    velocity = int(get_num(3, locate_col + 10))
    scr.present()

    # Flip angle for player 2
    if player_num == 2:
        angle = 180.0 - angle

    # Erase input lines
    for i in range(1, 5):
        txt.locate(i, 1)
        txt.print_semi(" " * 30)
        txt.locate(i, 50 // (80 // MaxCol))
        txt.print_semi(" " * 30)

    # Plot the shot
    return plot_shot(x, y, angle, velocity, player_num)


# ---------------------------------------------------------------------------
# PlotShot — BAS L905-1018
# ---------------------------------------------------------------------------
def plot_shot(start_x: int, start_y: int, angle_deg: float, velocity: int, player_num: int) -> int:
    """PlotShot — animate banana across screen. BAS L905-1018.
    Returns player number hit (0=no hit, 1/2=gorilla hit)."""
    global SunHit

    angle_rad = angle_deg / 180.0 * pi_
    # Radius = Mode MOD 7  # Computed but never used (quirk)

    init_xvel = math.cos(angle_rad) * velocity
    init_yvel = math.sin(angle_rad) * velocity

    oldx = float(start_x)
    oldy = float(start_y)

    # Draw gorilla toss pose
    if player_num == 1:
        gfx.put_sprite(start_x, start_y, GorL, action="PSET")
    else:
        gfx.put_sprite(start_x, start_y, GorR, action="PSET")
    scr.present()

    # Throw sound
    sound.play("MBo0L32A-L64CL16BL64A+")
    rest(0.1)

    # Redraw gorilla arms down
    gfx.put_sprite(start_x, start_y, GorD, action="PSET")
    scr.present()

    adjust = scl(4)
    xedge = scl(9) * (2 - player_num)

    impact = False
    shot_in_sun = False
    on_screen = True
    player_hit = 0
    need_erase = False

    start_xpos = float(start_x)
    start_ypos = float(start_y - adjust - 3)

    if player_num == 2:
        start_xpos = start_xpos + scl(25)
        direction = scl(4)
    else:
        direction = scl(-4)

    if velocity < 2:
        x_pos = float(start_x)
        y_pos = float(start_y)
        pointval = OBJECTCOLOR
    else:
        x_pos = start_xpos
        y_pos = start_ypos
        pointval = 0

    t = 0.0  # t#
    oldrot = 0

    while (not impact) and on_screen:
        rest(0.02)

        # Erase old banana
        if need_erase:
            need_erase = False
            draw_ban(oldx, oldy, oldrot, False)
            scr.present()

        # Physics
        x_pos = start_xpos + (init_xvel * t) + (0.5 * (Wind / 5.0) * t * t)
        y_pos = start_ypos + ((-1.0 * (init_yvel * t)) + (0.5 * gravity_ * t * t)) * (ScrHeight / 350.0)

        # Check if on screen
        if (x_pos >= ScrWidth - scl(10)) or (x_pos <= 3) or (y_pos >= ScrHeight - 3):
            on_screen = False

        if on_screen and y_pos > 0:
            look_y = 0
            look_x = scl(8 * (2 - player_num))

            while True:
                pv = scr.point(int(x_pos + look_x), int(y_pos + look_y))
                if pv == 0:
                    impact = False
                    if shot_in_sun:
                        if abs(ScrWidth // 2 - x_pos) > scl(20) or y_pos > SunHt:
                            shot_in_sun = False
                elif pv == SUNATTR and y_pos < SunHt:
                    if not SunHit:
                        do_sun(SUNSHOCK)
                        scr.present()
                    SunHit = TRUE
                    shot_in_sun = True
                else:
                    impact = True
                    pointval = pv

                if impact:
                    break

                look_x = look_x + direction
                look_y = look_y + scl(6)
                if look_x != scl(4):
                    break
                # Continue checking if look_x == scl(4)

            if not shot_in_sun and not impact:
                rot = int(t * 10) % 4
                draw_ban(x_pos, y_pos, rot, True)
                need_erase = True
                scr.present()

            oldx = x_pos
            oldy = y_pos
            oldrot = int(t * 10) % 4

        t = t + 0.1

    # End of flight
    if pointval != OBJECTCOLOR and impact:
        do_explosion(x_pos + adjust, y_pos + adjust)
    elif pointval == OBJECTCOLOR:
        player_hit = explode_gorilla(x_pos, y_pos)

    return player_hit


# ---------------------------------------------------------------------------
# DrawBan — BAS L370-400
# ---------------------------------------------------------------------------
def draw_ban(xc: float, yc: float, r: int, bc: bool) -> None:
    """DrawBan — draw or erase banana. BAS L370-400."""
    bananas = [LBan, UBan, DBan, RBan]  # r: 0=left, 1=up, 2=down, 3=right
    sprite = bananas[r]
    action = "PSET" if bc else "XOR"
    gfx.put_sprite(int(xc), int(yc), sprite, action=action)


# ---------------------------------------------------------------------------
# DoExplosion — BAS L253-270
# ---------------------------------------------------------------------------
def do_explosion(x: float, y: float) -> None:
    """DoExplosion — expanding/contracting explosion. BAS L253-270."""
    sound.play("MBO0L32EFGEFDC")

    radius = ScrHeight // 50
    if Mode == 9:
        inc = 0.5
    else:
        inc = 0.41

    # Expanding
    c = 0.0
    while c <= radius:
        gfx.circle(int(x), int(y), int(c), ExplosionColor)
        scr.present()
        c += inc

    # Contracting
    c = float(radius)
    while c >= 0:
        gfx.circle(int(x), int(y), int(c), BACKATTR)
        scr.present()
        # FOR i = 1 TO 100: NEXT i → negligible
        rest(0.005)
        c -= inc


# ---------------------------------------------------------------------------
# ExplodeGorilla — BAS L460-490
# ---------------------------------------------------------------------------
def explode_gorilla(x: float, y: float) -> int:
    """ExplodeGorilla — gorilla explosion animation. BAS L460-490.
    Returns the player number that was hit."""
    yadj = scl(12)
    xadj = scl(5)
    scl_x = ScrWidth / 320.0
    scl_y = ScrHeight / 200.0

    if x < ScrWidth / 2.0:
        player_hit = 1
    else:
        player_hit = 2

    sound.play("MBO0L16EFGEFDC")

    gx = GorillaX[player_hit]
    gy = GorillaY[player_hit]

    # Phase 1: expanding with lines
    for i in range(1, int(8 * scl_x) + 1):
        gfx.circle(
            int(gx + 3.5 * scl_x + xadj),
            int(gy + 7 * scl_y + yadj),
            i, ExplosionColor,
            aspect=1.57
        )
        gfx.line(
            int(gx + 7 * scl_x), int(gy + 9 * scl_y - i),
            int(gx), int(gy + 9 * scl_y - i),
            ExplosionColor
        )
        scr.present()

    # Phase 2: alternating color expansion
    for i in range(1, int(16 * scl_x) + 1):
        if i < 8 * scl_x:
            gfx.circle(
                int(gx + 3.5 * scl_x + xadj),
                int(gy + 7 * scl_y + yadj),
                int(8 * scl_x + 1 - i), BACKATTR,
                aspect=1.57
            )
        gfx.circle(
            int(gx + 3.5 * scl_x + xadj),
            int(gy + yadj),
            i, (i % 2) + 1,
            aspect=1.57
        )
        scr.present()

    # Phase 3: contracting
    for i in range(int(24 * scl_x), 0, -1):
        gfx.circle(
            int(gx + 3.5 * scl_x + xadj),
            int(gy + yadj),
            i, BACKATTR,
            aspect=1.57
        )
        # FOR Count = 1 TO 200: NEXT → negligible
        scr.present()

    return player_hit


# ---------------------------------------------------------------------------
# DoSun — BAS L328-368
# ---------------------------------------------------------------------------
def do_sun(mouth: int) -> None:
    """DoSun — draw sun with happy or shocked expression. BAS L328-368."""
    x = ScrWidth // 2
    y = scl(25)

    # Clear old sun
    gfx.line(x - scl(22), y - scl(18), x + scl(22), y + scl(18), BACKATTR, bf_flag=True)

    # Body
    gfx.circle(x, y, scl(12), SUNATTR)
    gfx.paint(x, y, SUNATTR)

    # Rays
    gfx.line(x - scl(20), y, x + scl(20), y, SUNATTR)
    gfx.line(x, y - scl(15), x, y + scl(15), SUNATTR)
    gfx.line(x - scl(15), y - scl(10), x + scl(15), y + scl(10), SUNATTR)
    gfx.line(x - scl(15), y + scl(10), x + scl(15), y - scl(10), SUNATTR)
    gfx.line(x - scl(8), y - scl(13), x + scl(8), y + scl(13), SUNATTR)
    gfx.line(x - scl(8), y + scl(13), x + scl(8), y - scl(13), SUNATTR)
    gfx.line(x - scl(18), y - scl(5), x + scl(18), y + scl(5), SUNATTR)
    gfx.line(x - scl(18), y + scl(5), x + scl(18), y - scl(5), SUNATTR)

    # Mouth
    if mouth:  # "O" mouth (shocked)
        gfx.circle(x, y + scl(5), scl(2.9), 0)
        gfx.paint(x, y + scl(5), 0, 0)
    else:  # Smile
        gfx.circle(x, y, scl(8), 0,
                   start_angle=210 * pi_ / 180,
                   end_angle=330 * pi_ / 180)

    # Eyes
    gfx.circle(x - 3, y - 2, 1, 0)
    gfx.circle(x + 3, y - 2, 1, 0)
    gfx.pset(x - 3, y - 2, 0)
    gfx.pset(x + 3, y - 2, 0)


# ---------------------------------------------------------------------------
# DrawGorilla — BAS L395-455
# ---------------------------------------------------------------------------
def draw_gorilla(x: int, y: int, arms: int) -> None:
    """DrawGorilla — draw gorilla and capture sprite. BAS L395-455."""
    global GorL, GorR, GorD

    # Head
    gfx.line(x - scl(4), y, x + scl(2.9), y + scl(6), OBJECTCOLOR, bf_flag=True)
    gfx.line(x - scl(5), y + scl(2), x + scl(4), y + scl(4), OBJECTCOLOR, bf_flag=True)

    # Eyes/brow
    gfx.line(x - scl(3), y + scl(2), x + scl(2), y + scl(2), 0)

    # Nose (EGA only)
    if Mode == 9:
        for i in range(-2, 0):
            gfx.pset(x + i, y + 4, 0)
            gfx.pset(x + i + 3, y + 4, 0)

    # Neck
    gfx.line(x - scl(3), y + scl(7), x + scl(2), y + scl(7), OBJECTCOLOR)

    # Body
    gfx.line(x - scl(8), y + scl(8), x + scl(6.9), y + scl(14), OBJECTCOLOR, bf_flag=True)
    gfx.line(x - scl(6), y + scl(15), x + scl(4.9), y + scl(20), OBJECTCOLOR, bf_flag=True)

    # Legs
    for i in range(5):
        gfx.circle(x + scl(i), y + scl(25), scl(10), OBJECTCOLOR,
                   start_angle=3 * pi_ / 4, end_angle=9 * pi_ / 8)
        gfx.circle(x + scl(-6) + scl(i - 0.1), y + scl(25), scl(10), OBJECTCOLOR,
                   start_angle=15 * pi_ / 8, end_angle=pi_ / 4)

    # Chest
    gfx.circle(x - scl(4.9), y + scl(10), scl(4.9), 0,
               start_angle=3 * pi_ / 2, end_angle=0)
    gfx.circle(x + scl(4.9), y + scl(10), scl(4.9), 0,
               start_angle=pi_, end_angle=3 * pi_ / 2)

    # Arms (and GET sprite capture)
    for i in range(-5, 0):
        if arms == RIGHTUP:
            gfx.circle(x + scl(i - 0.1), y + scl(14), scl(9), OBJECTCOLOR,
                       start_angle=3 * pi_ / 4, end_angle=5 * pi_ / 4)
            gfx.circle(x + scl(4.9) + scl(i), y + scl(4), scl(9), OBJECTCOLOR,
                       start_angle=7 * pi_ / 4, end_angle=pi_ / 4)
            GorR = gfx.get_sprite(x - scl(15), y - scl(1), x + scl(14), y + scl(28))

        elif arms == LEFTUP:
            gfx.circle(x + scl(i - 0.1), y + scl(4), scl(9), OBJECTCOLOR,
                       start_angle=3 * pi_ / 4, end_angle=5 * pi_ / 4)
            gfx.circle(x + scl(4.9) + scl(i), y + scl(14), scl(9), OBJECTCOLOR,
                       start_angle=7 * pi_ / 4, end_angle=pi_ / 4)
            GorL = gfx.get_sprite(x - scl(15), y - scl(1), x + scl(14), y + scl(28))

        elif arms == ARMSDOWN:
            gfx.circle(x + scl(i - 0.1), y + scl(14), scl(9), OBJECTCOLOR,
                       start_angle=3 * pi_ / 4, end_angle=5 * pi_ / 4)
            gfx.circle(x + scl(4.9) + scl(i), y + scl(14), scl(9), OBJECTCOLOR,
                       start_angle=7 * pi_ / 4, end_angle=pi_ / 4)
            GorD = gfx.get_sprite(x - scl(15), y - scl(1), x + scl(14), y + scl(28))


# ---------------------------------------------------------------------------
# MakeCityScape — BAS L689-815
# ---------------------------------------------------------------------------
def make_city_scape() -> list:
    """MakeCityScape — generate random skyline. BAS L689-815.
    Returns list of XYPoint building coordinates."""
    global Wind, LastBuilding

    bcoor = [XYPoint() for _ in range(31)]  # 0 TO 30

    x = 2

    slope = fn_ran(6)
    if slope == 1:
        new_ht = 15
    elif slope == 2:
        new_ht = 130
    elif slope in (3, 4, 5):
        new_ht = 15
    else:  # 6
        new_ht = 130

    if Mode == 9:
        bottom_line = 335
        ht_inc = 10
        def_bwidth = 37
        random_height = 120
        wwidth = 3
        wheight = 6
        wdif_v = 15
        wdif_h = 10
    else:
        bottom_line = 190
        ht_inc = 6
        new_ht = new_ht * 20 // 35
        def_bwidth = 18
        random_height = 54
        wwidth = 1
        wheight = 2
        wdif_v = 5
        wdif_h = 4

    cur_building = 1

    while True:
        if slope == 1:
            new_ht = new_ht + ht_inc
        elif slope == 2:
            new_ht = new_ht - ht_inc
        elif slope in (3, 4, 5):
            if x > ScrWidth // 2:
                new_ht = new_ht - 2 * ht_inc
            else:
                new_ht = new_ht + 2 * ht_inc
        # CASE 4 is unreachable (shadowed by CASE 3 TO 5) — preserved quirk

        bwidth = fn_ran(def_bwidth) + def_bwidth
        if x + bwidth > ScrWidth:
            bwidth = ScrWidth - x - 2

        bheight = fn_ran(random_height) + new_ht
        if bheight < ht_inc:
            bheight = ht_inc

        # Check too high
        if bottom_line - bheight <= GHeight:
            bheight = GHeight - 5

        bcoor[cur_building].xcoor = x
        bcoor[cur_building].ycoor = bottom_line - bheight

        if Mode == 9:
            building_color = fn_ran(3) + 4
        else:
            building_color = 2

        # Draw building: outline first, then filled
        gfx.line(x - 1, bottom_line + 1, x + bwidth + 1, bottom_line - bheight - 1,
                 BACKATTR, b_flag=True)
        gfx.line(x, bottom_line, x + bwidth, bottom_line - bheight,
                 building_color, bf_flag=True)

        # Windows
        c = x + 3
        while c < x + bwidth - 3:
            for i in range(bheight - 3, 7 - 1, -wdif_v):
                if Mode != 9:
                    win_colr = (fn_ran(2) - 2) * -3
                elif fn_ran(4) == 1:
                    win_colr = 8
                else:
                    win_colr = WINDOWCOLOR
                gfx.line(c, bottom_line - i, c + wwidth, bottom_line - i + wheight,
                         win_colr, bf_flag=True)
            c = c + wdif_h

        x = x + bwidth + 2
        cur_building = cur_building + 1

        if x > ScrWidth - ht_inc:
            break

    LastBuilding = cur_building - 1

    # Wind
    Wind = fn_ran(10) - 5
    if fn_ran(3) == 1:
        if Wind > 0:
            Wind = Wind + fn_ran(10)
        else:
            Wind = Wind - fn_ran(10)

    # Draw wind arrow
    if Wind != 0:
        wind_line = Wind * 3 * (ScrWidth // 320)
        gfx.line(ScrWidth // 2, ScrHeight - 5,
                 ScrWidth // 2 + wind_line, ScrHeight - 5, ExplosionColor)
        if Wind > 0:
            arrow_dir = -2
        else:
            arrow_dir = 2
        gfx.line(ScrWidth // 2 + wind_line, ScrHeight - 5,
                 ScrWidth // 2 + wind_line + arrow_dir, ScrHeight - 5 - 2,
                 ExplosionColor)
        gfx.line(ScrWidth // 2 + wind_line, ScrHeight - 5,
                 ScrWidth // 2 + wind_line + arrow_dir, ScrHeight - 5 + 2,
                 ExplosionColor)

    return bcoor


# ---------------------------------------------------------------------------
# PlaceGorillas — BAS L816-840
# ---------------------------------------------------------------------------
def place_gorillas(bcoor: list) -> None:
    """PlaceGorillas — PUT gorillas on buildings. BAS L816-840."""
    if Mode == 9:
        xadj = 14
        yadj = 30
    else:
        xadj = 7
        yadj = 16

    scl_x = ScrWidth / 320.0
    scl_y = ScrHeight / 200.0

    for i in range(1, 3):
        if i == 1:
            bnum = fn_ran(2) + 1
        else:
            bnum = LastBuilding - fn_ran(2)

        bwidth = bcoor[bnum + 1].xcoor - bcoor[bnum].xcoor
        GorillaX[i] = bcoor[bnum].xcoor + bwidth // 2 - xadj
        GorillaY[i] = bcoor[bnum].ycoor - yadj
        gfx.put_sprite(GorillaX[i], GorillaY[i], GorD, action="PSET")


# ---------------------------------------------------------------------------
# VictoryDance — BAS L1124-1136
# ---------------------------------------------------------------------------
def victory_dance(player: int) -> None:
    """VictoryDance — gorilla victory animation. BAS L1124-1136."""
    for _ in range(4):
        gfx.put_sprite(GorillaX[player], GorillaY[player], GorL, action="PSET")
        scr.present()
        sound.play("MFO0L32EFGEFDC")
        rest(0.2)
        gfx.put_sprite(GorillaX[player], GorillaY[player], GorR, action="PSET")
        scr.present()
        sound.play("MFO0L32EFGEFDC")
        rest(0.2)
    # Redraw arms down
    gfx.put_sprite(GorillaX[player], GorillaY[player], GorD, action="PSET")
    scr.present()


# ---------------------------------------------------------------------------
# UpdateScores — BAS L1112-1122
# ---------------------------------------------------------------------------
def update_scores(total_wins: list, tosser: int, hit: int) -> None:
    """UpdateScores — BAS L1112-1122.
    
    NOTE: This function is not currently used. Score logic is inline in play_game().
    
    Args:
        total_wins: List of win counts for each player
        tosser: Player who threw the banana (1 or 2)
        hit: Player who was hit (1 or 2)
    """
    # If thrower hit themselves, opponent gets the point
    if hit == tosser:
        other = 3 - tosser
        total_wins[other] = total_wins[other] + 1
    else:
        # Thrower hit opponent, thrower gets the point
        total_wins[tosser] = total_wins[tosser] + 1


# ---------------------------------------------------------------------------
# ClearGorillas — (not explicitly in source; implicit in mode switch)
# ---------------------------------------------------------------------------
def clear_gorillas() -> None:
    """ClearGorillas — erase gorillas from screen."""
    # In the original, gorillas are erased by redrawing with background.
    # For the port, we just re-PUT them with XOR to erase.
    if GorD is not None:
        gfx.put_sprite(GorillaX[1], GorillaY[1], GorD, action="XOR")
        gfx.put_sprite(GorillaX[2], GorillaY[2], GorD, action="XOR")


# ---------------------------------------------------------------------------
# GorillaIntro — BAS L583-660
# ---------------------------------------------------------------------------
def gorilla_intro(player1: str, player2: str) -> None:
    """GorillaIntro — show gorillas, capture sprites, dance animation. BAS L583-660."""
    global GorL, GorR, GorD

    # Print choice prompt (still on SCREEN 0 from get_inputs)
    txt.locate(16, 34)
    txt.print_("--------------")
    txt.locate(18, 34)
    txt.print_("V = View Intro")
    txt.locate(19, 34)
    txt.print_("P = Play Game")
    txt.locate(21, 35)
    txt.print_("Your Choice?")
    scr.present()

    ch = ""
    while ch == "":
        ch = kbd.inkey()
        if not ch:
            import pygame
            pygame.time.wait(10)

    if Mode == 1:
        x = 125
        y = 100
    else:
        x = 278
        y = 175

    # Re-enter graphics mode (clears screen)
    scr.screen(Mode)
    txt.init()
    set_screen()

    if Mode == 1:
        center(5, "Please wait while gorillas are drawn.")
        scr.present()

    # VIEW PRINT 9 TO 24 — restrict graphics drawing area
    txt.view_print(9, 24)

    # Hide gorilla via palette trick (EGA only)
    if Mode == 9:
        scr.set_palette_color(OBJECTCOLOR, BackColor)

    # Capture sprites: draw, CLS 2 (clear graphics only), repeat
    draw_gorilla(x, y, ARMSDOWN)
    txt.cls(mode_flag=2)  # CLS 2 — clear text viewport but not graphics? No — CLS 2 clears graphics only.
    # Actually in QBASIC, CLS 2 clears the VIEW PRINT graphics area.
    # For sprite capture, we just need the sprites stored, the screen gets cleared after.
    draw_gorilla(x, y, LEFTUP)
    txt.cls(mode_flag=2)
    draw_gorilla(x, y, RIGHTUP)
    txt.cls(mode_flag=2)

    # Restore VIEW PRINT and reveal gorillas
    txt.view_print(1, 25)
    if Mode == 9:
        scr.set_palette_color(OBJECTCOLOR, 46)  # orange

    if ucase(ch) == "V":
        # Show "STARRING" animation
        center(2, "Q B A S I C   G O R I L L A S")
        center(5, "             STARRING:               ")
        p_str = player1 + " AND " + player2
        center(7, p_str)
        scr.present()

        # Show two gorillas side by side
        gfx.put_sprite(x - 13, y, GorD, action="PSET")
        gfx.put_sprite(x + 47, y, GorD, action="PSET")
        scr.present()
        rest(1)

        # Dance sequence 1
        gfx.put_sprite(x - 13, y, GorL, action="PSET")
        gfx.put_sprite(x + 47, y, GorR, action="PSET")
        scr.present()
        sound.play("t120o1l16b9n0baan0bn0bn0baaan0b9n0baan0b")
        rest(0.3)

        # Dance sequence 2
        gfx.put_sprite(x - 13, y, GorR, action="PSET")
        gfx.put_sprite(x + 47, y, GorL, action="PSET")
        scr.present()
        sound.play("o2l16e-9n0e-d-d-n0e-n0e-n0e-d-d-d-n0e-9n0e-d-d-n0e-")
        rest(0.3)

        # Dance sequence 3
        gfx.put_sprite(x - 13, y, GorL, action="PSET")
        gfx.put_sprite(x + 47, y, GorR, action="PSET")
        scr.present()
        sound.play("o2l16g-9n0g-een0g-n0g-n0g-eeen0g-9n0g-een0g-")
        rest(0.3)

        # Dance sequence 4
        gfx.put_sprite(x - 13, y, GorR, action="PSET")
        gfx.put_sprite(x + 47, y, GorL, action="PSET")
        scr.present()
        sound.play("o2l16b9n0baan0g-n0g-n0g-eeen0o1b9n0baan0b")
        rest(0.3)

        # Finale loop
        for _ in range(4):
            gfx.put_sprite(x - 13, y, GorL, action="PSET")
            gfx.put_sprite(x + 47, y, GorR, action="PSET")
            scr.present()
            sound.play("T160O0L32EFGEFDC")
            rest(0.1)
            gfx.put_sprite(x - 13, y, GorR, action="PSET")
            gfx.put_sprite(x + 47, y, GorL, action="PSET")
            scr.present()
            sound.play("T160O0L32EFGEFDC")
            rest(0.1)

    # Clear screen before returning to game
    scr.cls()
    scr.present()


# ---------------------------------------------------------------------------
# PlayGame — BAS L843-888
# ---------------------------------------------------------------------------
def play_game(player1: str, player2: str, num_games: int) -> None:
    """PlayGame — main game loop. BAS L843-888."""
    global SunHit, MaxCol

    total_wins = [0, 0, 0]  # 1-indexed: total_wins[1], total_wins[2]
    j = 1

    for game_i in range(1, num_games + 1):
        scr.screen(Mode)
        txt.init()
        set_screen()
        scr.cls()

        rng.randomize()  # RANDOMIZE (TIMER)

        bcoor = make_city_scape()
        place_gorillas(bcoor)
        do_sun(SUNHAPPY)
        scr.present()

        hit = False
        while not hit:
            j = 1 - j
            txt.locate(1, 1)
            txt.print_(player1)
            txt.locate(1, MaxCol - len(player2))
            txt.print_(player2)
            center(23, ltrim(qb_str(total_wins[1])) + ">Score<" + ltrim(qb_str(total_wins[2])))
            scr.present()

            tosser = j + 1
            tossee = 3 - j

            hit = do_shot(tosser, GorillaX[tosser], GorillaY[tosser])

            if SunHit:
                do_sun(SUNHAPPY)
                scr.present()

            if hit:
                # hit is the player who was hit (1 or 2)
                # If thrower hit themselves, opponent gets the point
                if hit == tosser:
                    other = 3 - tosser
                    total_wins[other] = total_wins[other] + 1
                    victory_dance(other)
                else:
                    # Thrower hit opponent, thrower gets the point
                    total_wins[tosser] = total_wins[tosser] + 1
                    victory_dance(tosser)
                scr.present()

        timing.sleep(1)

    # Game over screen
    scr.screen(0)
    txt.init()
    # WIDTH 80, 25
    txt.color(7, 0)
    MaxCol = 80
    txt.cls()

    center(8, "GAME OVER!")
    center(10, "Score:")
    txt.locate(11, 30)
    txt.print_semi(player1)
    txt.tab(50)
    txt.print_(str(total_wins[1]))
    txt.locate(12, 30)
    txt.print_semi(player2)
    txt.tab(50)
    txt.print_(str(total_wins[2]))
    center(24, "Press any key to continue")
    scr.present()
    sparkle_pause()
    txt.color(7, 0)
    txt.cls()
    scr.present()


# ---------------------------------------------------------------------------
# Load banana sprite data
# ---------------------------------------------------------------------------
def load_banana_sprites() -> None:
    """Load banana sprites from DATA (BAS L125-143, InitVars L157-181)."""
    global LBan, RBan, UBan, DBan

    if Mode == 9:
        # EGA banana DATA (BAS L135-143)
        ega_left =  [458758, 202116096, 471604224, 943208448, 943208448, 943208448, 471604224, 202116096, 0]
        ega_down =  [262153, -2134835200, -2134802239, -2130771968, -2130738945, 8323072, 8323199, 4063232, 4063294]
        ega_up =    [262153, 4063232, 4063294, 8323072, 8323199, -2130771968, -2130738945, -2134835200, -2134802239]
        ega_right = [458758, -1061109760, -522133504, 1886416896, 1886416896, 1886416896, -522133504, -1061109760, 0]

        u32 = lambda longs: [v & 0xFFFFFFFF for v in longs]
        LBan = gfx.decode_put_data(u32(ega_left), bpp=4)
        DBan = gfx.decode_put_data(u32(ega_down), bpp=4)
        UBan = gfx.decode_put_data(u32(ega_up), bpp=4)
        RBan = gfx.decode_put_data(u32(ega_right), bpp=4)
    else:
        # CGA banana DATA (BAS L125-133)
        cga_left =  [327686, -252645316, 60]
        cga_down =  [196618, -1057030081, 49344]
        cga_up =    [196618, -1056980800, 63]
        cga_right = [327686, 1010580720, 240]

        u32 = lambda longs: [v & 0xFFFFFFFF for v in longs]
        LBan = gfx.decode_put_data(u32(cga_left), bpp=2)
        DBan = gfx.decode_put_data(u32(cga_down), bpp=2)
        UBan = gfx.decode_put_data(u32(cga_up), bpp=2)
        RBan = gfx.decode_put_data(u32(cga_right), bpp=2)


# ---------------------------------------------------------------------------
# InitVars (GOSUB target) — BAS L142-212
# ---------------------------------------------------------------------------
def init_vars() -> None:
    """InitVars — initialize screen mode, load sprites, calibrate speed.
    BAS L142-212."""
    global Mode, ScrWidth, ScrHeight, GHeight, MachSpeed, SunHt, MaxCol

    # Try SCREEN 9 first (EGA)
    Mode = 9
    try:
        scr.screen(Mode)
        txt.init()
    except Exception:
        # Fallback to SCREEN 1 (CGA)
        Mode = 1
        scr.screen(Mode)
        txt.init()

    MachSpeed = calc_delay()

    if Mode == 9:
        ScrWidth = 640
        ScrHeight = 350
        GHeight = 25
        SunHt = 39
    else:
        ScrWidth = 320
        ScrHeight = 200
        GHeight = 12
        MachSpeed = MachSpeed * 1.3
        SunHt = 20

    # Load banana sprites
    load_banana_sprites()

    MaxCol = 80 if Mode == 9 else 40


# ===========================================================================
# Main program — BAS L110-123
# ===========================================================================
def main():
    global Mode, MaxCol

    # Initialize pygame + runtime
    scr.init(scale=args.scale, fullscreen=args.fullscreen, mute=args.mute, speed=args.speed)
    timing.set_speed(args.speed)
    sound.init(mute=args.mute)
    rng.randomize()

    # NumLock POKE — no-op in port (QUIRKS.md #7)

    # GOSUB InitVars
    init_vars()

    # Intro
    intro()

    # GetInputs
    name1, name2, num_games = get_inputs()

    # GorillaIntro
    gorilla_intro(name1, name2)

    # PlayGame
    play_game(name1, name2, num_games)

    # Restore NumLock — no-op

    # Clean up
    import pygame
    pygame.quit()


if __name__ == "__main__":
    main()
