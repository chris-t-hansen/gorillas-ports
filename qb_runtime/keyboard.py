"""qb_runtime.keyboard — INKEY$, INPUT, key mapping.

Maps pygame key events to QBASIC INKEY$ return values:
  - Enter = chr(13), Esc = chr(27), Backspace = chr(8), Tab = chr(9)
  - Arrows = chr(0) + chr(72/80/75/77) (up/down/left/right)
  - Printable ASCII characters map directly.

OS key-repeat is used (documented choice — see QUIRKS.md).
"""

import pygame

from . import screen as scr
from . import text as txt


# ---------------------------------------------------------------------------
# Key mapping tables
# ---------------------------------------------------------------------------

# Extended key scan codes (returned as chr(0) + chr(code)).
_EXTENDED_KEYS = {
    pygame.K_UP: 72,
    pygame.K_DOWN: 80,
    pygame.K_LEFT: 75,
    pygame.K_RIGHT: 77,
    pygame.K_HOME: 71,
    pygame.K_END: 79,
    pygame.K_PAGEUP: 73,
    pygame.K_PAGEDOWN: 81,
    pygame.K_INSERT: 82,
    pygame.K_DELETE: 83,
    pygame.K_F1: 59,
    pygame.K_F2: 60,
    pygame.K_F3: 61,
    pygame.K_F4: 62,
    pygame.K_F5: 63,
    pygame.K_F6: 64,
    pygame.K_F7: 65,
    pygame.K_F8: 66,
    pygame.K_F9: 67,
    pygame.K_F10: 68,
    pygame.K_F11: 133,
    pygame.K_F12: 134,
}


# ---------------------------------------------------------------------------
# Key buffer
# ---------------------------------------------------------------------------

_key_buffer: list = []  # list of INKEY$-style strings


def _process_events() -> None:
    """Process pygame events and fill the key buffer."""
    events = scr.pump()
    for ev in events:
        if ev.type == pygame.KEYDOWN:
            key_str = _event_to_inkey(ev)
            if key_str is not None:
                _key_buffer.append(key_str)


def _event_to_inkey(ev) -> str:
    """Convert a pygame KEYDOWN event to an INKEY$ string."""
    key = ev.key

    # Check extended keys first.
    if key in _EXTENDED_KEYS:
        return chr(0) + chr(_EXTENDED_KEYS[key])

    # Special keys.
    if key == pygame.K_RETURN:
        return chr(13)
    if key == pygame.K_ESCAPE:
        return chr(27)
    if key == pygame.K_BACKSPACE:
        return chr(8)
    if key == pygame.K_TAB:
        return chr(9)

    # Printable ASCII.
    if ev.unicode and len(ev.unicode) == 1:
        ch = ev.unicode
        code = ord(ch)
        if 32 <= code <= 126:
            return ch
        if code == 13:
            return chr(13)

    return None


# ---------------------------------------------------------------------------
# INKEY$
# ---------------------------------------------------------------------------


def inkey() -> str:
    """INKEY$ — return next key from buffer, or empty string.

    Processes pending pygame events before checking.
    """
    _process_events()
    if _key_buffer:
        return _key_buffer.pop(0)
    return ""


def flush() -> None:
    """Clear the keyboard buffer (WHILE INKEY$ <> "": WEND)."""
    _process_events()
    _key_buffer.clear()


# ---------------------------------------------------------------------------
# Wait for any key
# ---------------------------------------------------------------------------


def wait_key() -> str:
    """Wait for any key press, returning the INKEY$ value.

    Pumps events and presents the screen while waiting.
    """
    flush()
    while True:
        _process_events()
        if _key_buffer:
            return _key_buffer.pop(0)
        scr.present()
        pygame.time.wait(10)


# ---------------------------------------------------------------------------
# LINE INPUT — prompt with "? " and read a string
# ---------------------------------------------------------------------------


def line_input(prompt: str = "") -> str:
    """LINE INPUT prompt$; var$ — display prompt with '? ' and read a line.

    Handles backspace and Enter. Returns the entered string.
    """
    # Print prompt + "? " without newline.
    if prompt:
        txt.print_semi(prompt)
    txt.print_semi("? ")
    scr.present()

    result = []
    while True:
        k = inkey()
        if not k:
            scr.present()
            pygame.time.wait(10)
            continue

        if k == chr(13):
            # Enter — done.
            txt.print_()  # newline
            scr.present()
            return "".join(result)
        elif k == chr(8):
            # Backspace.
            if result:
                result.pop()
                # Move cursor back and erase.
                row, col = txt.get_cursor_pos()
                if col > 0:
                    txt.set_cursor_pos(row, col - 1)
                    txt.print_semi(" ")
                    txt.set_cursor_pos(row, col - 1)
        elif len(k) == 1 and ord(k) >= 32:
            result.append(k)
            txt.print_semi(k)

        scr.present()


# ---------------------------------------------------------------------------
# INPUT — prompt with "? " and read/parse a value
# ---------------------------------------------------------------------------


def input_str(prompt: str = "") -> str:
    """INPUT prompt$; var$ — display prompt with '? ' and read a string.

    QBASIC INPUT prints '? ' after the prompt. Invalid numeric input
    triggers 'Redo from start'. This function returns the raw string;
    the caller handles type validation and redo logic.
    """
    return line_input(prompt)


def input_number(prompt: str = "", as_float: bool = True):
    """INPUT with numeric validation.

    Repeats until a valid number is entered. Returns the parsed number.
    On invalid input, prints 'Redo from start' and retries.
    """
    from .format import val

    while True:
        s = input_str(prompt)
        s = s.strip()
        if not s:
            # Empty input → redo.
            txt.print_("Redo from start")
            scr.present()
            continue
        v = val(s)
        if v == 0.0 and s not in ("0", "0.", ".0", "0.0"):
            # VAL returned 0 but input wasn't "0" → invalid.
            txt.print_("Redo from start")
            scr.present()
            continue
        if not as_float:
            return int(v)
        return v


# ---------------------------------------------------------------------------
# GetNum# — numeric entry with INKEY$ polling
# ---------------------------------------------------------------------------


def get_num(row: int, col: int, max_value: float = 360.0) -> float:
    """GetNum#(Row, Col) — INKEY$-based numeric entry.

    Accepts digits 0-9, one decimal point, Enter (rejects > max_value),
    Backspace. Any other key → BEEP. Returns the entered number.
    Echoes result with underscore cursor.
    """
    from .format import val

    # Clear keyboard buffer.
    flush()

    txt.locate(row, col)
    result = ""

    while True:
        # Display current result with underscore cursor.
        txt.locate(row, col)
        display = result + chr(95) + "    "  # underscore + padding
        txt.print_semi(display)
        scr.present()

        k = inkey()
        if not k:
            pygame.time.wait(10)
            continue

        if k == chr(13):
            # Enter.
            v = val(result) if result else 0.0
            if v > max_value:
                # Reject: clear and restart.
                result = ""
                continue
            return v
        elif k == chr(8):
            # Backspace.
            if result:
                result = result[:-1]
        elif k in "0123456789":
            result += k
        elif k == ".":
            if "." not in result:
                result += k
        else:
            # Invalid key — BEEP (sound.py should provide beep()).
            pass  # beep() called from sound module