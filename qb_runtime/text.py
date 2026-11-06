"""qb_runtime.text — text grid, PRINT, LOCATE, COLOR, cursor, scrolling.

Maintains a parallel text grid (chars + attributes) for:
- State inspection and golden-file tests
- Scroll support (VIEW PRINT)
- Full redraw on demand

PRINT semantics:
  - Semicolon (;) → no advance (next print continues at same position)
  - Comma (,) → advance to next 14-column print zone
  - No separator → newline after print
  - Numbers: leading space (positive) or minus (negative), trailing space
  - Trailing semicolon suppresses newline

LOCATE is 1-based (row 1..rows, col 1..cols).

Cursor blinks at ~1.875 Hz (VGA rate: ~266 ms on, ~266 ms off).
"""

import time
import numpy as np

from . import screen as scr
from .format import qb_str, space as space_str


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

# Text grid: chars[row][col] = CP437 code, attrs[row][col] = (fg, bg, blink)
_grid_chars: np.ndarray = None  # shape (rows, cols), dtype uint8
_grid_attrs: list = None  # list of rows, each a list of (fg, bg, blink) tuples

# Current text color
_fg: int = 7  # light gray (default)
_bg: int = 0  # black
_blink: bool = False

# Cursor position (0-based internally; LOCATE uses 1-based)
_cur_row: int = 0
_cur_col: int = 0

# Cursor visibility
_cursor_visible: bool = False

# VIEW PRINT range (0-based row indices; -1 means inactive)
_vp_top: int = -1
_vp_bot: int = -1

# Last separator used (for PRINT chaining): ';' or ',' or None (newline)
_last_sep: str = None

# Blink timing
_BLINK_PERIOD = 0.533  # seconds (~1.875 Hz: 266ms on, 266ms off)
_blink_on: bool = True
_blink_last: float = 0.0

# Dirty flag (text grid changed, needs redraw)
_dirty: bool = True


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def init() -> None:
    """Initialize or reset text state. Call after screen.screen() or CLS."""
    global _grid_chars, _grid_attrs, _cur_row, _cur_col, _dirty
    global _fg, _bg, _blink, _vp_top, _vp_bot, _last_sep, _cursor_visible

    r = scr.rows()
    c = scr.cols()
    _grid_chars = np.full((r, c), 32, dtype=np.uint8)  # spaces
    _grid_attrs = [[(7, 0, False)] * c for _ in range(r)]
    _cur_row = 0
    _cur_col = 0
    _fg = 7
    _bg = 0
    _blink = False
    _vp_top = -1
    _vp_bot = -1
    _last_sep = None
    _cursor_visible = False
    _dirty = True


# ---------------------------------------------------------------------------
# LOCATE (1-based)
# ---------------------------------------------------------------------------


def locate(row: int = -1, col: int = -1, cursor: int = -1) -> None:
    """LOCATE [row][, col][, cursor].

    row/col are 1-based. -1 means "don't change".
    cursor: -1 = don't change, 0 = invisible, 1 = visible.
    """
    global _cur_row, _cur_col, _cursor_visible

    if row >= 1:
        _cur_row = min(row - 1, scr.rows() - 1)
    if col >= 1:
        _cur_col = min(col - 1, scr.cols() - 1)
    if cursor >= 0:
        _cursor_visible = cursor == 1


# ---------------------------------------------------------------------------
# COLOR
# ---------------------------------------------------------------------------


def color(fg: int = -1, bg: int = -1) -> None:
    """COLOR [fg][, bg]. -1 means don't change.

    fg 0-15: foreground color. fg >= 16: color (fg-16) with blink.
    bg 0-7: background color (EGA: 0-15 in some modes).
    """
    global _fg, _bg, _blink

    if fg >= 0:
        _blink = fg >= 16
        _fg = fg & 0x0F
    if bg >= 0:
        _bg = bg & 0x0F


# ---------------------------------------------------------------------------
# VIEW PRINT
# ---------------------------------------------------------------------------


def view_print(top: int = -1, bot: int = -1) -> None:
    """VIEW PRINT top TO bot (1-based row numbers). -1 to deactivate."""
    global _vp_top, _vp_bot
    if top < 0:
        _vp_top = -1
        _vp_bot = -1
    else:
        _vp_top = top - 1
        _vp_bot = bot - 1


def get_view_print():
    """Return (top, bot) 0-based, or (-1, -1) if inactive."""
    return _vp_top, _vp_bot


# ---------------------------------------------------------------------------
# Scrolling
# ---------------------------------------------------------------------------


def _scroll_up() -> None:
    """Scroll the text grid up by one line within the VIEW PRINT region."""
    top = _vp_top if _vp_top >= 0 else 0
    bot = _vp_bot if _vp_bot >= 0 else scr.rows() - 1

    # Shift grid up.
    _grid_chars[top:bot, :] = _grid_chars[top + 1 : bot + 1, :]
    _grid_chars[bot, :] = 32  # blank bottom line
    _grid_attrs[top:bot] = _grid_attrs[top + 1 : bot + 1]
    _grid_attrs[bot] = [(7, 0, False)] * scr.cols()

    # Scroll the framebuffer too.
    fb = scr.fb()
    ch = scr.cell_height()
    y_top = top * ch
    y_bot = (bot + 1) * ch
    fb[y_top : y_bot - ch, :] = fb[y_top + ch : y_bot, :]
    fb[y_bot - ch : y_bot, :] = 0  # clear bottom line


# ---------------------------------------------------------------------------
# Glyph blit (write a character into the framebuffer)
# ---------------------------------------------------------------------------


def _blit_char(row: int, col: int, code: int, fg: int, bg: int) -> None:
    """Blit a CP437 glyph into the framebuffer at (row, col)."""
    fb = scr.fb()
    glyph = scr.get_glyph(code)
    cw = scr.cell_width()
    ch = scr.cell_height()
    off_y = scr.font_offset_y()

    x0 = col * cw
    y0 = row * ch

    # glyph shape: (cw, glyph_h). Blit at y0 - off_y + appropriate offset.
    # Actually: the glyph content starts at row `off_y` of the rendered surface.
    # We want to place it at y0, so we blit glyph rows [off_y : off_y + ch]
    # into fb rows [y0 : y0 + ch].
    gh = glyph.shape[1]
    src_start = min(off_y, gh)
    src_end = min(off_y + ch, gh)
    dst_start = y0
    dst_end = y0 + (src_end - src_start)

    if src_end <= src_start:
        return

    g = glyph[:, src_start:src_end]  # shape (cw, blit_h)
    blit_h = src_end - src_start

    # Fill background for the cell.
    fb[y0 : y0 + ch, x0 : x0 + cw] = bg

    # Where glyph is foreground (1), write fg color.
    for dy in range(blit_h):
        for dx in range(cw):
            if g[dx, dy]:
                fb[dst_start + dy, x0 + dx] = fg


# ---------------------------------------------------------------------------
# Redraw
# ---------------------------------------------------------------------------


def redraw() -> None:
    """Redraw the entire text grid into the framebuffer."""
    r = scr.rows()
    c = scr.cols()
    for row in range(r):
        for col in range(c):
            code = int(_grid_chars[row, col])
            fg, bg, _blink = _grid_attrs[row][col]
            _blit_char(row, col, code, fg, bg)
    _dirty = False


# ---------------------------------------------------------------------------
# PRINT helpers
# ---------------------------------------------------------------------------


def _advance_newline() -> None:
    """Move cursor to next line, scrolling if needed."""
    global _cur_row, _cur_col

    _cur_col = 0
    bot = _vp_bot if _vp_bot >= 0 else scr.rows() - 1

    if _cur_row >= bot:
        _scroll_up()
    else:
        _cur_row += 1


def _write_char(code: int) -> None:
    """Write one character at the current cursor position and advance."""
    global _cur_col, _dirty

    c = scr.cols()

    if _cur_col >= c:
        _advance_newline()

    _grid_chars[_cur_row, _cur_col] = code & 0xFF
    _grid_attrs[_cur_row][_cur_col] = (_fg, _bg, _blink)
    _blit_char(_cur_row, _cur_col, code, _fg, _bg)
    _cur_col += 1
    _dirty = True


def _advance_zone() -> None:
    """Advance to the next 14-column print zone (comma separator)."""
    global _cur_col

    c = scr.cols()
    # Zones start at columns 1, 15, 29, 43, 57, 71 (1-based) = 0, 14, 28, 42, 56, 70 (0-based).
    zone_size = 14
    next_zone = ((_cur_col // zone_size) + 1) * zone_size
    if next_zone >= c:
        _advance_newline()
        _cur_col = 0
    else:
        _cur_col = next_zone


# ---------------------------------------------------------------------------
# PRINT (main entry point)
# ---------------------------------------------------------------------------


def print_(value=None, sep: str = None) -> None:
    """PRINT a value with optional separator.

    Args:
        value: The value to print. None means "print empty line" (if sep is None).
        sep: The trailing separator:
            ';' → no advance (cursor stays after last char)
            ',' → advance to next print zone
            None → newline after print (default)

    Numeric values get a leading space (positive) or minus (negative) and a
    trailing space.
    """
    global _last_sep

    # Handle "PRINT" with no args → print empty line.
    if value is None and sep is None:
        _advance_newline()
        _last_sep = None
        return

    if value is not None:
        # Convert to string.
        if isinstance(value, str):
            s = value
        elif isinstance(value, int):
            # Integer: leading space + digits + trailing space.
            s = qb_str(value) + " "
        elif isinstance(value, float):
            s = qb_str(value) + " "
        else:
            s = str(value)

        for ch in s:
            code = ord(ch)
            if code == 10:  # LF → newline
                _advance_newline()
            elif code == 13:  # CR → carriage return
                _cur_col = 0
            elif code == 8:  # BS → backspace
                if _cur_col > 0:
                    _cur_col -= 1
            elif code == 9:  # TAB → advance to next 8-col tab stop
                next_tab = ((_cur_col // 8) + 1) * 8
                while _cur_col < next_tab:
                    _write_char(32)  # space
            elif code < 32 and code != 7:
                # Control codes: most are printable glyphs in CP437.
                # But some (7 = BEL) are non-printing. Just skip non-printing.
                if code == 7:
                    pass  # BEEP — sound.py should handle
                else:
                    _write_char(code)
            else:
                _write_char(code)

    # Handle separator.
    if sep == ";":
        _last_sep = ";"
    elif sep == ",":
        _advance_zone()
        _last_sep = ","
    else:
        # No separator → newline.
        _advance_newline()
        _last_sep = None


def print_semi(value=None) -> None:
    """PRINT with semicolon separator (no advance)."""
    print_(value, sep=";")


def print_comma(value=None) -> None:
    """PRINT with comma separator (advance to next zone)."""
    print_(value, sep=",")


# ---------------------------------------------------------------------------
# TAB() and SPC()
# ---------------------------------------------------------------------------


def tab(n: int) -> None:
    """TAB(n) — move cursor to column n (1-based)."""
    global _cur_col
    c = scr.cols()
    target = n - 1  # convert to 0-based
    if target < 0:
        target = 0
    if target < _cur_col:
        # TAB to a column before current → next line.
        _advance_newline()
        _cur_col = target
    elif target >= c:
        _advance_newline()
        _cur_col = target % c
    else:
        # Fill with spaces from current position to target.
        while _cur_col < target:
            _write_char(32)


def spc(n: int) -> None:
    """SPC(n) — print n spaces."""
    for _ in range(max(0, n)):
        _write_char(32)


# ---------------------------------------------------------------------------
# Cursor rendering
# ---------------------------------------------------------------------------


def draw_cursor() -> None:
    """Draw the cursor if visible and it's the "on" phase of the blink cycle."""
    global _blink_on, _blink_last

    if not _cursor_visible:
        return

    now = time.monotonic()
    if now - _blink_last >= _BLINK_PERIOD / 2:
        _blink_on = not _blink_on
        _blink_last = now

    if not _blink_on:
        return

    # Draw an underscore-style cursor: bottom 2 rows of the cell.
    fb = scr.fb()
    cw = scr.cell_width()
    ch = scr.cell_height()
    x0 = _cur_col * cw
    y0 = _cur_row * ch
    fb[y0 + ch - 2 : y0 + ch, x0 : x0 + cw] = _fg


def erase_cursor() -> None:
    """Erase the cursor by re-blitting the character underneath."""
    if not _cursor_visible:
        return
    row, col = _cur_row, _cur_col
    code = int(_grid_chars[row, col])
    fg, bg, _ = _grid_attrs[row][col]
    _blit_char(row, col, code, fg, bg)


# ---------------------------------------------------------------------------
# CLS (text-aware)
# ---------------------------------------------------------------------------


def cls(mode_flag: int = 0) -> None:
    """CLS with text grid support.

    mode_flag:
      0 → clear everything (screen + text grid)
      1 → clear graphics only (no-op here; screen.cls handles fb)
      2 → clear text only (text grid + text region of fb)
    """
    global _cur_row, _cur_col, _dirty

    if mode_flag == 1:
        # Graphics-only clear — screen.cls handles this.
        return

    top = _vp_top if _vp_top >= 0 else 0
    bot = _vp_bot if _vp_bot >= 0 else scr.rows() - 1

    # Clear text grid in the active region.
    _grid_chars[top : bot + 1, :] = 32
    for r in range(top, bot + 1):
        _grid_attrs[r] = [(7, 0, False)] * scr.cols()

    # Clear framebuffer in the active region.
    scr.cls(mode_flag=0, view_print_top=top, view_print_bot=bot)

    # Reset cursor to top-left of active region.
    _cur_row = top
    _cur_col = 0
    _dirty = True


# ---------------------------------------------------------------------------
# INPUT helpers (for keyboard.py to use)
# ---------------------------------------------------------------------------


def get_cursor_pos():
    """Return (row, col) 0-based."""
    return _cur_row, _cur_col


def set_cursor_pos(row: int, col: int) -> None:
    """Set cursor position (0-based)."""
    global _cur_row, _cur_col
    _cur_row = row
    _cur_col = col
