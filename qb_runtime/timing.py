"""qb_runtime.timing — TIMER, SLEEP, Rest, and all delay handling.

Single source of truth for time. All timing constants live here with
comments citing source lines and reasoning.

Key design (from FOLLOWUP.md research):
  Rest(t#) ≈ t# seconds on the author's reference machine, scaled by
  MachSpeed / SPEEDCONST. For the port: Rest(t#) → wall-clock wait
  of t# / speed_multiplier seconds.

  TIMER = seconds since local midnight (~55 ms resolution on real hardware).
  Implemented via time.monotonic() with midnight rollover preserved.
"""

import time
import datetime

import pygame

from . import screen as scr


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# SPEEDCONST from gorilla.bas L60.
SPEEDCONST = 500

# Speed multiplier (from --speed flag). 1.0 = "intended" speed.
_speed_multiplier: float = 1.0


def set_speed(multiplier: float) -> None:
    """Set the global speed multiplier."""
    global _speed_multiplier
    _speed_multiplier = max(0.01, multiplier)


def get_speed() -> float:
    return _speed_multiplier


# ---------------------------------------------------------------------------
# TIMER — seconds since local midnight
# ---------------------------------------------------------------------------

# Epoch for our TIMER emulation. We use real local time, so midnight rollover
# behaves like the original (TIMER resets at midnight).
_epoch_date = datetime.date.today()


def timer() -> float:
    """TIMER — seconds since local midnight.

    QBASIC TIMER has ~55 ms resolution (1/18.2 s). We return higher resolution
    but the semantics match. Handles midnight rollover.
    """
    global _epoch_date
    now = datetime.datetime.now()
    # Check for midnight rollover.
    if now.date() != _epoch_date:
        _epoch_date = now.date()
    midnight = datetime.datetime(now.year, now.month, now.day)
    return (now - midnight).total_seconds()


# ---------------------------------------------------------------------------
# Delay with event pumping
# ---------------------------------------------------------------------------


def _pump_wait(seconds: float) -> None:
    """Wait for *seconds* while pumping pygame events and presenting.

    Never blocks the window — events are processed and screen is refreshed
    during the wait. Routes events through keyboard module so INKEY$ sees
    keypresses that arrive during the wait.
    """
    from . import keyboard as kbd

    end = time.monotonic() + seconds
    while time.monotonic() < end:
        kbd._process_events()  # pumps events AND fills key buffer
        scr.present()
        remaining = end - time.monotonic()
        if remaining > 0.01:
            pygame.time.wait(min(10, int(remaining * 1000)))


# ---------------------------------------------------------------------------
# Rest(t#) — main game delay
# ---------------------------------------------------------------------------


def rest(t: float) -> None:
    """Rest(t#) — busy-wait equivalent.

    QBASIC: busy-waits until TIMER - s# > MachSpeed * t# / SPEEDCONST.
    Port: wall-clock wait of t# / speed_multiplier seconds.

    Callers in gorilla.bas:
      DoExplosion: Rest .005 per ring          (L266)
      GorillaIntro: Rest 1, .3, .1             (L630-648)
      PlotShot: Rest .1 (throw), .02 (per frame) (L927, L956)
      VictoryDance: Rest .2                     (L1126)
    """
    delay = t / _speed_multiplier
    _pump_wait(delay)


# ---------------------------------------------------------------------------
# SLEEP — real seconds, any key ends early
# ---------------------------------------------------------------------------


def sleep(seconds: float = 0) -> bool:
    """SLEEP [n].

    n > 0: wait n real seconds. Any key press ends early.
    n = 0: wait for any key press (SLEEP with no argument).

    Returns True if interrupted by a key, False if timed out.
    """
    from . import keyboard as kbd

    if seconds <= 0:
        # Wait for keypress indefinitely.
        kbd.wait_key()
        return True

    end = time.monotonic() + seconds
    while time.monotonic() < end:
        k = kbd.inkey()  # inkey() already pumps events via _process_events()
        if k:
            return True  # interrupted
        scr.present()
        remaining = end - time.monotonic()
        if remaining > 0.01:
            pygame.time.wait(min(10, int(remaining * 1000)))
    return False


# ---------------------------------------------------------------------------
# MachSpeed — calibrated machine speed (for compatibility)
# ---------------------------------------------------------------------------

# In the original, CalcDelay! counted iterations in 0.5s → MachSpeed.
# For the port, we don't need this for timing (Rest uses wall-clock),
# but game code references it. Set to SPEEDCONST so Rest(t#) = t# seconds
# at speed_multiplier = 1.0.

MachSpeed: float = float(SPEEDCONST)


def calc_delay() -> float:
    """CalcDelay! equivalent. Returns MachSpeed (fixed, not calibrated)."""
    return MachSpeed
