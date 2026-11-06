"""qb_runtime.screen — screen modes, indexed framebuffer, palette, window, fonts.

Provides a numpy uint8 indexed framebuffer (H, W) with a 16-entry RGB palette
applied at present-time only (palette changes affect already-drawn pixels).

Supports SCREEN 0 (text, 640x350, 8x14 font), SCREEN 1 (CGA, 320x200, 8x8 font),
and SCREEN 9 (EGA, 640x350, 8x14 font).
"""

import os
import sys
import math
import numpy as np

import pygame

# ---------------------------------------------------------------------------
# Assets path
# ---------------------------------------------------------------------------
_ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"
)
_FONTS_DIR = os.path.join(_ASSETS_DIR, "fonts")

# ---------------------------------------------------------------------------
# Font file names
# ---------------------------------------------------------------------------
_FONT_EGA_8x14 = "Bm437_IBM_EGA_8x14.otb"
_FONT_CGA_8x8 = "Bm437_IBM_CGA.otb"

# ---------------------------------------------------------------------------
# Standard CGA/VGA 16-color text palette (exact values from SKILL.md)
# ---------------------------------------------------------------------------
CGA_TEXT_PALETTE = [
    (0x00, 0x00, 0x00),  # 0 black
    (0x00, 0x00, 0xAA),  # 1 blue
    (0x00, 0xAA, 0x00),  # 2 green
    (0x00, 0xAA, 0xAA),  # 3 cyan
    (0xAA, 0x00, 0x00),  # 4 red
    (0xAA, 0x00, 0xAA),  # 5 magenta
    (0xAA, 0x55, 0x00),  # 6 brown
    (0xAA, 0xAA, 0xAA),  # 7 light gray
    (0x55, 0x55, 0x55),  # 8 dark gray
    (0x55, 0x55, 0xFF),  # 9 light blue
    (0x55, 0xFF, 0x55),  # 10 light green
    (0x55, 0xFF, 0xFF),  # 11 light cyan
    (0xFF, 0x55, 0x55),  # 12 light red
    (0xFF, 0x55, 0xFF),  # 13 light magenta
    (0xFF, 0xFF, 0x55),  # 14 yellow
    (0xFF, 0xFF, 0xFF),  # 15 white
]

# ---------------------------------------------------------------------------
# EGA 64-color decode
# ---------------------------------------------------------------------------


def ega_decode(v: int):
    """Decode a 6-bit EGA color value to (R, G, B) with 0/85/170/255 levels.

    Bit layout: [Sr Sg Sb | R G B] = [b5 b4 b3 | b2 b1 b0]
    Primary bits (lower 3): contribute 0xAA (170).
    Secondary bits (upper 3): contribute 0x55 (85).
    """
    v = v & 0x3F
    r = 0xAA * ((v >> 2) & 1) + 0x55 * ((v >> 5) & 1)
    g = 0xAA * ((v >> 1) & 1) + 0x55 * ((v >> 4) & 1)
    b = 0xAA * (v & 1) + 0x55 * ((v >> 3) & 1)
    return (r, g, b)


# SCREEN 9 default palette registers (attribute → EGA value).
# Note: attribute 6 = EGA 20 = brown (0xAA, 0x55, 0x00), NOT EGA 6.
EGA_DEFAULT_REGISTERS = [0, 1, 2, 3, 4, 5, 20, 7, 56, 57, 58, 59, 60, 61, 62, 63]


def ega_default_palette():
    """Return the default SCREEN 9 palette as a list of 16 (R,G,B) tuples."""
    return [ega_decode(v) for v in EGA_DEFAULT_REGISTERS]


# ---------------------------------------------------------------------------
# Screen mode geometry
# ---------------------------------------------------------------------------

# (width, height, cell_w, cell_h, cols, rows)
_MODE_GEOMETRY = {
    0: (640, 350, 8, 14, 80, 25),
    1: (320, 200, 8, 8, 40, 25),
    9: (640, 350, 8, 14, 80, 25),
}

# ---------------------------------------------------------------------------
# CGA palettes
# ---------------------------------------------------------------------------

# CGA Palette 0: Black, Cyan, Magenta, White
CGA_PALETTE_0 = [
    (0x00, 0x00, 0x00),  # 0 Black
    (0x55, 0xFF, 0xFF),  # 1 Cyan
    (0xFF, 0x55, 0xFF),  # 2 Magenta
    (0xFF, 0xFF, 0xFF),  # 3 White
]

# CGA Palette 1: Black, Green, Red, Yellow (high intensity)
CGA_PALETTE_1 = [
    (0x00, 0x00, 0x00),  # 0 Black
    (0x55, 0xFF, 0x55),  # 1 Green
    (0xFF, 0x55, 0x55),  # 2 Red
    (0xFF, 0xFF, 0x55),  # 3 Yellow
]


# ---------------------------------------------------------------------------
# Module-level state (singleton screen)
# ---------------------------------------------------------------------------

_window: pygame.Surface = None
_fb: np.ndarray = None  # indexed framebuffer, shape (H, W), dtype uint8
_palette: list = None  # list of 16 (R,G,B) tuples (4 for CGA)
_mode: int = -1
_fb_w: int = 0
_fb_h: int = 0
_cell_w: int = 0
_cell_h: int = 0
_cols: int = 0
_rows: int = 0
_cga_palette_select: int = 0  # CGA palette 0 or 1
_cga_bg_color: int = 0  # CGA background color (0-15)

# Font: pre-rendered glyph masks (numpy uint8 arrays, 0=bg, 1=fg)
_glyphs: list = None  # list of 256 numpy arrays
_font_offset_y: int = 0  # vertical offset for blitting (ascent adjustment)
_font_cell_h: int = 0  # cell height (14 or 8)

# Display
_scale: int = 0  # 0 = auto-fit
_fullscreen: bool = False
_mute: bool = False
_speed: float = 1.0

# Render surface (reused each frame)
_render_surf: pygame.Surface = None


# ---------------------------------------------------------------------------
# CP437 → Unicode mapping
# ---------------------------------------------------------------------------


def _cp437_to_unicode(code: int) -> str:
    """Convert a CP437 byte (0-255) to a Unicode character."""
    return bytes([code & 0xFF]).decode("cp437")


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------


def _load_font(filename: str, size: int):
    """Load a Px437 .otb font and pre-render all 256 CP437 glyphs.

    Returns (glyphs, offset_y, cell_h) where:
      glyphs: list of 256 numpy uint8 arrays (cell_w × actual_h), 0=bg 1=fg
      offset_y: vertical offset for blitting (to align glyph to cell)
      cell_h: the cell height (size parameter)
    """
    font_path = os.path.join(_FONTS_DIR, filename)
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font not found: {font_path}")

    font = pygame.font.Font(font_path, size)
    cell_w = 8  # all our fonts are 8-pixel wide

    # Detect vertical offset by rendering a full-block glyph (U+2588).
    full_block = font.render("\u2588", False, (255, 255, 255), (0, 0, 0))
    fb_arr = pygame.surfarray.array2d(full_block)
    rows_with_content = np.any(fb_arr.T != 0, axis=1)
    if np.any(rows_with_content):
        first_row = np.argmax(rows_with_content)
    else:
        first_row = 0
    offset_y = first_row

    # Pre-render all 256 CP437 glyphs as numpy masks.
    glyphs = []
    for code in range(256):
        # CP437 codes 0-31 are printable glyphs (smileys etc.), not control chars.
        # Codes 8, 9, 10, 13 are control chars in Unicode but glyphs in CP437.
        # We use the Unicode mapping for rendering, but override for control codes.
        if code == 0:
            # Null → blank glyph
            mask = np.zeros((cell_w, size), dtype=np.uint8)
        elif code in (8, 9, 10, 13):
            # These are control codes that QBASIC handles specially.
            # Render as blank for now; text.py intercepts them.
            mask = np.zeros((cell_w, size), dtype=np.uint8)
        else:
            ch = _cp437_to_unicode(code)
            surf = font.render(ch, False, (255, 255, 255), (0, 0, 0))
            arr = pygame.surfarray.array2d(surf)  # shape (surf_w, surf_h)
            # Convert to mask: non-zero = foreground.
            mask = (arr != 0).astype(np.uint8)
            # Pad or crop to cell_w width if needed.
            if mask.shape[0] != cell_w:
                new_mask = np.zeros((cell_w, mask.shape[1]), dtype=np.uint8)
                copy_w = min(cell_w, mask.shape[0])
                new_mask[:copy_w] = mask[:copy_w]
                mask = new_mask
        glyphs.append(mask)

    return glyphs, offset_y, size


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def init(scale: int = 0, fullscreen: bool = False, mute: bool = False, speed: float = 1.0):
    """Initialize pygame and create the display window.

    Args:
        scale: Integer scale factor. 0 = auto-fit to display.
        fullscreen: Start in fullscreen mode.
        mute: Disable sound.
        speed: Speed multiplier for timing.
    """
    global _scale, _fullscreen, _mute, _speed

    _scale = scale
    _fullscreen = fullscreen
    _mute = mute
    _speed = speed

    pygame.init()
    pygame.display.set_caption("Gorillas")

    # Start with SCREEN 0 (text mode).
    screen(0)


def _create_window(display_w: int, display_h: int, force_recreate: bool = False):
    """Create or resize the pygame window.
    
    Args:
        display_w: Desired window width
        display_h: Desired window height
        force_recreate: If True, always recreate the window even if size matches
    """
    global _window, _render_surf

    flags = 0
    if _fullscreen:
        flags |= pygame.FULLSCREEN

    if _window is not None and not force_recreate:
        # Check if current window matches desired size.
        cur_w, cur_h = _window.get_size()
        if cur_w == display_w and cur_h == display_h:
            # Even if size matches, recreate render surface for mode switch
            _render_surf = pygame.Surface((_fb_w, _fb_h))
            return  # already correct size

    # Force window recreation by quitting and reinitializing display
    if _window is not None:
        pygame.display.quit()
        pygame.display.init()
    
    _window = pygame.display.set_mode((display_w, display_h), flags)
    _render_surf = pygame.Surface((_fb_w, _fb_h))


def _compute_display_size(fb_w: int, fb_h: int):
    """Compute window size maintaining 4:3 display aspect ratio.

    For SCREEN 9 (640x350): display at 640x480 (4:3 with PAR 1:1.371).
    For SCREEN 1 (320x200): display at 320x240 (4:3 with PAR 1:1.2).
    Then scale by _scale factor.
    """
    # Compute 4:3 display height: width * 3 / 4
    display_w = fb_w
    display_h = int(fb_w * 3 / 4)

    if _scale > 0:
        display_w *= _scale
        display_h *= _scale
    else:
        # Auto-fit: find the largest integer scale that fits the display.
        info = pygame.display.Info()
        screen_w, screen_h = info.current_w, info.current_h
        # Use 80% of screen as max.
        max_w = int(screen_w * 0.8)
        max_h = int(screen_h * 0.8)
        auto_scale = max(1, min(max_w // display_w, max_h // display_h))
        display_w *= auto_scale
        display_h *= auto_scale

    return display_w, display_h


# ---------------------------------------------------------------------------
# Screen mode switching
# ---------------------------------------------------------------------------


def screen(mode: int) -> None:
    """Switch to the given screen mode (0, 1, or 9). Clears framebuffer and palette."""
    global _mode, _fb, _palette, _fb_w, _fb_h, _cell_w, _cell_h, _cols, _rows
    global _glyphs, _font_offset_y, _font_cell_h

    if mode not in _MODE_GEOMETRY:
        raise ValueError(f"Unsupported screen mode: {mode}")

    # Always reinitialize, even if mode hasn't changed (QBASIC SCREEN clears everything)
    _mode = mode
    _fb_w, _fb_h, _cell_w, _cell_h, _cols, _rows = _MODE_GEOMETRY[mode]

    # Create framebuffer (all zeros = background color, attribute 0).
    _fb = np.zeros((_fb_h, _fb_w), dtype=np.uint8)

    # Set default palette.
    if mode == 0:
        _palette = list(CGA_TEXT_PALETTE)  # SCREEN 0 uses full 16-color text palette
    elif mode == 1:
        _palette = list(CGA_PALETTE_1)  # SCREEN 1 uses 4-color CGA graphics palette
        # Initialize CGA with palette 1 (green/red/yellow) by default
        set_cga_palette(1, 0)
    else:
        _palette = ega_default_palette()

    # Load appropriate font.
    if mode == 1:
        _glyphs, _font_offset_y, _font_cell_h = _load_font(_FONT_CGA_8x8, 8)
    else:
        _glyphs, _font_offset_y, _font_cell_h = _load_font(_FONT_EGA_8x14, 14)

    # Create/resize window.
    display_w, display_h = _compute_display_size(_fb_w, _fb_h)
    _create_window(display_w, display_h, force_recreate=True)


# ---------------------------------------------------------------------------
# Framebuffer access
# ---------------------------------------------------------------------------


def fb() -> np.ndarray:
    """Return the indexed framebuffer (shape (H, W), dtype uint8)."""
    return _fb


def fb_width() -> int:
    return _fb_w


def fb_height() -> int:
    return _fb_h


def mode() -> int:
    return _mode


def cell_width() -> int:
    return _cell_w


def cell_height() -> int:
    return _cell_h


def cols() -> int:
    return _cols


def rows() -> int:
    return _rows


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------


def get_palette() -> list:
    """Return a copy of the current 16-entry palette [(R,G,B), ...]."""
    return list(_palette)


def set_palette_color(attr: int, value) -> None:
    """Set palette register *attr* (0-15).

    *value* can be:
      - An int (EGA 6-bit value, decoded via ega_decode)
      - A (R, G, B) tuple
      
    For CGA mode (mode 1), only indices 0-3 are valid.
    """
    if _mode == 1:
        # CGA mode: only 4 colors (0-3)
        if attr > 3:
            return
        if isinstance(value, int):
            # In CGA, int values map to 16-color text palette
            if 0 <= value < len(CGA_TEXT_PALETTE):
                _palette[attr] = CGA_TEXT_PALETTE[value]
        else:
            _palette[attr] = tuple(value)
    else:
        # EGA mode: 16 colors
        attr = attr & 0x0F
        if isinstance(value, int):
            _palette[attr] = ega_decode(value)
        else:
            _palette[attr] = tuple(value)


def set_cga_palette(palette_num: int, bg_color: int = 0) -> None:
    """Set CGA palette for SCREEN 1.
    
    Args:
        palette_num: 0 for Palette 0 (cyan/magenta/white), 1 for Palette 1 (green/red/yellow)
        bg_color: Background color index (0-15) from CGA text palette
    """
    global _cga_palette_select, _cga_bg_color
    
    if _mode != 1:
        return  # Only valid in CGA mode
    
    _cga_palette_select = palette_num & 1
    _cga_bg_color = bg_color & 0x0F
    
    # Set the 4-color palette
    base_palette = CGA_PALETTE_0 if _cga_palette_select == 0 else CGA_PALETTE_1
    
    # Index 0: background color from 16-color palette
    if 0 <= bg_color < len(CGA_TEXT_PALETTE):
        _palette[0] = CGA_TEXT_PALETTE[bg_color]
    else:
        _palette[0] = (0, 0, 0)
    
    # Indices 1-3: colors from selected palette
    _palette[1] = base_palette[1]
    _palette[2] = base_palette[2]
    _palette[3] = base_palette[3]


# ---------------------------------------------------------------------------
# CLS
# ---------------------------------------------------------------------------


def cls(mode_flag: int = 0, view_print_top: int = 0, view_print_bot: int = -1) -> None:
    """Clear screen.

    mode_flag:
      0 → clear entire screen
      1 → clear graphics but not text (no-op in our model: clears fb only)
      2 → clear text but not graphics (clears text grid only — handled by text.py)

    view_print_top/bot: if set (VIEW PRINT active), only clear rows in range.
    """
    if view_print_bot < 0:
        view_print_bot = _rows - 1

    if mode_flag == 2:
        # Text-only clear — text.py handles this.
        return

    if view_print_top > 0 or view_print_bot < _rows - 1:
        # Clear only the VIEW PRINT region (pixel rows).
        y0 = view_print_top * _cell_h
        y1 = (view_print_bot + 1) * _cell_h
        _fb[y0:y1, :] = 0
    else:
        _fb[:] = 0


# ---------------------------------------------------------------------------
# Point (read pixel)
# ---------------------------------------------------------------------------


def point(x: int, y: int) -> int:
    """Read the palette index at (x, y). Returns 0 if out of bounds."""
    if 0 <= x < _fb_w and 0 <= y < _fb_h:
        return int(_fb[y, x])
    return 0


# ---------------------------------------------------------------------------
# Glyph access (for text.py)
# ---------------------------------------------------------------------------


def get_glyph(code: int):
    """Return the pre-rendered glyph mask for CP437 code (0-255).

    Returns a numpy uint8 array of shape (cell_w, glyph_h), values 0 or 1.
    """
    return _glyphs[code & 0xFF]


def font_offset_y() -> int:
    """Return the vertical offset for glyph blitting."""
    return _font_offset_y


# ---------------------------------------------------------------------------
# Event pump and present
# ---------------------------------------------------------------------------


def pump() -> list:
    """Pump the pygame event queue. Returns the list of events.

    Call this regularly during waits to keep the window responsive.
    """
    events = pygame.event.get()
    for ev in events:
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit(0)
    return events


def present() -> None:
    """Blit the indexed framebuffer to the window with the current palette,
    then flip the display.
    """
    if _window is None or _render_surf is None:
        return

    # Build RGB surface from indexed framebuffer + palette.
    pal_arr = np.array(_palette, dtype=np.uint8)  # (16, 3)
    rgb = pal_arr[_fb]  # shape (H, W, 3)

    # Create a pygame surface from the RGB array.
    surf = pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))

    # Blit to render surface, then scale to window.
    _render_surf.blit(surf, (0, 0))

    # Scale to window size with nearest-neighbor.
    win_w, win_h = _window.get_size()
    scaled = pygame.transform.scale(_render_surf, (win_w, win_h))
    _window.blit(scaled, (0, 0))
    pygame.display.flip()
