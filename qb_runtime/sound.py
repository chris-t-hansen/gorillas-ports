"""qb_runtime.sound — PLAY macro parser, BEEP, SOUND via pygame.mixer + numpy.

Generates square waves (50% duty cycle) to mimic the PC speaker.
Sample rate: 22050 Hz, 16-bit mono.

PLAY macro features supported:
  M B/F   — background / foreground
  O n     — octave (0-6)
  L n     — note length (1-64, default 4 = quarter note)
  T n     — tempo in quarter notes per minute (32-255, default 120)
  V n     — volume (0-15)
  N n     — play note by number (0-84, 0=rest)
  A-G     — notes, with optional # / + (sharp) or - (flat)
  P n     — pause (rest) in note-length units
  .       — dotted note (1.5x duration)
  < >     — octave down / up
  MN      — normal (7/8 of note duration sounds)
  ML      — legato (full duration)
  MS      — staccato (3/4 duration)
  MF      — foreground (synchronous)
  MB      — background (asynchronous, in a thread)
"""

import threading
import time
import re
import math

import numpy as np

# pygame.mixer may not be available in headless mode.
try:
    import pygame
    import pygame.mixer

    _mixer_available = True
except (ImportError, pygame.error):
    _mixer_available = False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SAMPLE_RATE = 22050
_MUTED = False
_bg_thread: threading.Thread = None


def init(mute: bool = False) -> None:
    """Initialize the sound system."""
    global _MUTED
    _MUTED = mute
    if not mute and _mixer_available:
        try:
            pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=1, buffer=512)
        except Exception as e:
            # Sound disabled, but log the error for debugging
            import sys
            print(f"Warning: pygame.mixer.init() failed: {e}", file=sys.stderr)


def set_mute(mute: bool) -> None:
    global _MUTED
    _MUTED = mute


# ---------------------------------------------------------------------------
# Square wave generation
# ---------------------------------------------------------------------------


def _square_wave(freq: float, duration: float, volume: float = 1.0) -> np.ndarray:
    """Generate a 50% duty cycle square wave.

    Args:
        freq: frequency in Hz
        duration: duration in seconds
        volume: 0.0 to 1.0

    Returns numpy int16 array.
    """
    n_samples = int(_SAMPLE_RATE * duration)
    if n_samples <= 0 or freq <= 0:
        return np.zeros(n_samples, dtype=np.int16)

    t = np.arange(n_samples)
    # Square wave: sign of sine.
    wave = np.sign(np.sin(2 * math.pi * freq * t / _SAMPLE_RATE))
    # Apply volume (max amplitude = 32767 * volume).
    wave = (wave * 32767 * volume * 0.5).astype(np.int16)
    return wave


def _play_sample(samples: np.ndarray) -> None:
    """Play a numpy int16 array through pygame.mixer."""
    if _MUTED:
        return
    if not _mixer_available:
        return
    if not pygame.mixer.get_init():
        # Mixer not initialized
        return
    try:
        # Convert mono to stereo if needed
        if samples.ndim == 1:
            # Duplicate mono samples for both stereo channels
            stereo = np.column_stack((samples, samples))
            sound = pygame.sndarray.make_sound(stereo)
        else:
            sound = pygame.sndarray.make_sound(samples)
        sound.play()
        # Wait for completion.
        while pygame.mixer.get_busy():
            pygame.time.wait(5)
    except Exception as e:
        import sys
        print(f"Warning: sound playback failed: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# BEEP — ~800 Hz for ~0.25 seconds
# ---------------------------------------------------------------------------


def beep() -> None:
    """BEEP — 800 Hz square wave for 0.25 seconds."""
    samples = _square_wave(800, 0.25, volume=0.5)
    _play_sample(samples)


# ---------------------------------------------------------------------------
# SOUND freq, duration (duration in 18.2 ticks per second)
# ---------------------------------------------------------------------------


def sound(freq: int, duration_ticks: int) -> None:
    """SOUND freq, duration.

    freq: 37-32767 Hz.
    duration: in clock ticks at 18.2 ticks/second.
    """
    duration_s = duration_ticks / 18.2
    if freq < 37:
        # Inaudible — just wait.
        time.sleep(duration_s)
        return
    samples = _square_wave(freq, duration_s, volume=0.5)
    _play_sample(samples)


# ---------------------------------------------------------------------------
# PLAY macro parser
# ---------------------------------------------------------------------------

# Note frequencies (equal temperament, A4 = 440 Hz).
# Note numbers: 0 = rest, 1 = C0, ..., 84 = B7.
# But PLAY uses N 0-84 where N1 = C1. We'll use a standard mapping.

_NOTE_NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _note_freq(note_num: int) -> float:
    """Convert note number (0=rest, 1=C0, ..., 84=B7) to frequency.

    PLAY O0 C = note 1 = MIDI 12 (C0, ~16.35 Hz).
    PLAY O4 C = note 49 = MIDI 60 (C4 middle C, ~261.6 Hz).
    Formula: midi = note_num + 11.
    """
    if note_num <= 0:
        return 0.0
    # Map to MIDI: O4 C (note 49) = MIDI 60 (middle C).
    midi = note_num + 11
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


class _PlayState:
    """Internal state for PLAY macro execution."""

    def __init__(self):
        self.octave = 4  # O4 = middle C octave
        self.length = 4  # L4 = quarter note
        self.tempo = 120  # T120 = 120 quarter notes per minute
        self.volume = 15  # V15 = max volume
        self.articulation = 7 / 8  # MN = normal (7/8 sounding)
        self.background = False  # MB = background
        self.foreground = True  # MF = foreground (default)

    def note_duration(self, length: int = None) -> float:
        """Duration of a note in seconds."""
        L = length if length else self.length
        # Quarter note = 60 / tempo seconds.
        # Whole note = 4 * quarter note.
        # Note of length L = whole note / L = 4 * (60 / tempo) / L.
        return 4.0 * (60.0 / self.tempo) / L

    def apply_dots(self, duration: float, macro: str, pos: int) -> tuple:
        """Apply dots (each adds 50% of previous). Returns (new_duration, new_pos)."""
        while pos < len(macro) and macro[pos] == ".":
            duration *= 1.5
            pos += 1
        return duration, pos


def _parse_play(macro: str) -> list:
    """Parse a PLAY macro string into a list of (frequency, duration_s) events.

    Returns list of (freq, duration) tuples. freq=0 means rest.
    """
    state = _PlayState()
    events = []
    i = 0
    n = len(macro)

    while i < n:
        ch = macro[i].upper()

        if ch == "M":
            i += 1
            if i < n:
                mod = macro[i].upper()
                if mod == "B":
                    state.background = True
                    state.foreground = False
                elif mod == "F":
                    state.foreground = True
                    state.background = False
                elif mod == "N":
                    state.articulation = 7 / 8  # normal
                elif mod == "L":
                    state.articulation = 1.0  # legato
                elif mod == "S":
                    state.articulation = 3 / 4  # staccato
            i += 1

        elif ch == "O":
            i += 1
            num, i = _parse_number(macro, i)
            state.octave = max(0, min(6, num))

        elif ch == "L":
            i += 1
            num, i = _parse_number(macro, i)
            state.length = max(1, min(64, num))

        elif ch == "T":
            i += 1
            num, i = _parse_number(macro, i)
            state.tempo = max(32, min(255, num))

        elif ch == "V":
            i += 1
            num, i = _parse_number(macro, i)
            state.volume = max(0, min(15, num))

        elif ch == "N":
            i += 1
            num, i = _parse_number(macro, i)
            freq = _note_freq(num)
            dur = state.note_duration()  # Total duration (note + rest)
            sound_dur = dur * state.articulation  # How long note sounds
            rest_dur = dur - sound_dur  # Rest after note
            sound_dur, i = state.apply_dots(sound_dur, macro, i)
            rest_dur, i = state.apply_dots(rest_dur, macro, i) if rest_dur > 0 else (rest_dur, i)
            events.append((freq, sound_dur))
            if rest_dur > 0:
                events.append((0.0, rest_dur))  # Rest

        elif ch in _NOTE_NAMES:
            base_note = _NOTE_NAMES[ch]
            i += 1
            # Check for sharp/flat.
            if i < n and macro[i] in ("#", "+"):
                base_note += 1
                i += 1
            elif i < n and macro[i] == "-":
                base_note -= 1
                i += 1
            # Convert to note number: C in current octave.
            # Octave 0 = C0, etc.
            note_num = state.octave * 12 + base_note + 1  # +1 because N1=C1
            freq = _note_freq(note_num)
            dur = state.note_duration()  # Total duration (note + rest)
            sound_dur = dur * state.articulation  # How long note sounds
            rest_dur = dur - sound_dur  # Rest after note
            sound_dur, i = state.apply_dots(sound_dur, macro, i)
            rest_dur, i = state.apply_dots(rest_dur, macro, i) if rest_dur > 0 else (rest_dur, i)
            events.append((freq, sound_dur))
            if rest_dur > 0:
                events.append((0.0, rest_dur))  # Rest

        elif ch == "P":
            i += 1
            num, i = _parse_number(macro, i)
            if num > 0:
                dur = state.note_duration(num)
                dur, i = state.apply_dots(dur, macro, i)
                events.append((0.0, dur))

        elif ch == "<":
            state.octave = max(0, state.octave - 1)
            i += 1

        elif ch == ">":
            state.octave = min(6, state.octave + 1)
            i += 1

        else:
            i += 1  # skip unknown

    return events


def _parse_number(macro: str, pos: int) -> tuple:
    """Parse a decimal number starting at pos. Returns (value, new_pos)."""
    start = pos
    while pos < len(macro) and macro[pos].isdigit():
        pos += 1
    if pos == start:
        return 0, pos
    return int(macro[start:pos]), pos


# ---------------------------------------------------------------------------
# PLAY execution
# ---------------------------------------------------------------------------


def play(macro: str) -> None:
    """PLAY macro$ — parse and execute a PLAY macro string.

    If the macro contains MB, plays in a background thread.
    Otherwise plays synchronously (blocking).
    """
    events = _parse_play(macro)

    # Check if background mode was specified.
    is_background = "MB" in macro.upper() or "mb" in macro

    if is_background:
        global _bg_thread
        _bg_thread = threading.Thread(target=_play_events, args=(events,), daemon=True)
        _bg_thread.start()
    else:
        _play_events(events)


def _play_events(events: list) -> None:
    """Play a list of (freq, duration) events."""
    for freq, dur in events:
        if freq > 0 and dur > 0:
            samples = _square_wave(freq, dur, volume=state_volume())
            _play_sample(samples)
        elif dur > 0:
            # Rest — just wait.
            if not _MUTED:
                time.sleep(dur)


def state_volume() -> float:
    """Return current volume as 0.0-1.0."""
    return 15 / 15.0 * 0.5  # default V15 → 50% amplitude


# ---------------------------------------------------------------------------
# Silence / stop
# ---------------------------------------------------------------------------


def stop() -> None:
    """Stop all playing sounds."""
    if _mixer_available:
        try:
            pygame.mixer.stop()
        except Exception:
            pass
