"""qb_runtime.graphics — PSET, LINE, CIRCLE, PAINT, POINT, GET, PUT.

All drawing operations work on the indexed framebuffer (numpy uint8).
Own rasterizers are used (no pygame.draw) to match QBASIC's pixel output.
"""

import math
import numpy as np
from collections import deque

from . import screen as scr


# ---------------------------------------------------------------------------
# PSET / PRESET
# ---------------------------------------------------------------------------


def pset(x: int, y: int, color: int = -1) -> None:
    """PSET (x, y)[, color]. color=-1 uses current foreground."""
    fb = scr.fb()
    if 0 <= x < scr.fb_width() and 0 <= y < scr.fb_height():
        if color < 0:
            color = 15
        # Clamp color to palette size (4 for CGA, 16 for EGA)
        max_color = 3 if scr.mode() == 1 else 15
        fb[y, x] = color & max_color


def preset(x: int, y: int) -> None:
    """PRESET (x, y) — set pixel to the complement of color 0 (always 0 in QBASIC)."""
    fb = scr.fb()
    if 0 <= x < scr.fb_width() and 0 <= y < scr.fb_height():
        fb[y, x] = 0


# ---------------------------------------------------------------------------
# LINE — Bresenham + B (box) + BF (filled box) + style patterns
# ---------------------------------------------------------------------------


def _plot_line(x0: int, y0: int, x1: int, y1: int, color: int) -> None:
    """Bresenham line from (x0,y0) to (x1,y1).

    Standard implementation matching QBASIC's LINE output.
    Both error conditions use the same e2 snapshot and can fire
    independently (allowing diagonal steps when e2 falls in both ranges).
    """
    fb = scr.fb()
    h, w = fb.shape
    
    # Clamp color to palette size (4 for CGA, 16 for EGA)
    max_color = 3 if scr.mode() == 1 else 15
    color = color & max_color

    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        if 0 <= x0 < w and 0 <= y0 < h:
            fb[y0, x0] = color
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def line(
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: int = -1,
    style: str = "",
    b_flag: bool = False,
    bf_flag: bool = False,
) -> None:
    """LINE [(x0,y0)]-(x1,y1)[, color][, B|BF][, style].

    style: 16-bit pattern (e.g. &HAAAA for dashed). Empty = solid.
    """
    if color < 0:
        color = 15
    
    # Clamp color to palette size (4 for CGA, 16 for EGA)
    max_color = 3 if scr.mode() == 1 else 15
    color = color & max_color

    if bf_flag:
        # Filled box.
        fb = scr.fb()
        left, right = min(x0, x1), max(x0, x1)
        top, bot = min(y0, y1), max(y0, y1)
        left = max(0, left)
        top = max(0, top)
        right = min(scr.fb_width() - 1, right)
        bot = min(scr.fb_height() - 1, bot)
        if left <= right and top <= bot:
            fb[top : bot + 1, left : right + 1] = color
    elif b_flag:
        # Box outline.
        _plot_line(x0, y0, x1, y0, color)  # top
        _plot_line(x1, y0, x1, y1, color)  # right
        _plot_line(x1, y1, x0, y1, color)  # bottom
        _plot_line(x0, y1, x0, y0, color)  # left
    else:
        # Single line with optional style pattern.
        if style:
            _plot_line_styled(x0, y0, x1, y1, color, style)
        else:
            _plot_line(x0, y0, x1, y1, color)


def _plot_line_styled(
    x0: int, y0: int, x1: int, y1: int, color: int, pattern: int
) -> None:
    """Draw a styled line using a 16-bit pattern mask."""
    fb = scr.fb()
    h, w = fb.shape

    # Clamp color to palette size (4 for CGA, 16 for EGA)
    max_color = 3 if scr.mode() == 1 else 15
    color = color & max_color

    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    bit_pos = 15  # start from MSB
    while True:
        if 0 <= x0 < w and 0 <= y0 < h:
            if (pattern >> bit_pos) & 1:
                fb[y0, x0] = color
        bit_pos = (bit_pos - 1) & 15
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


# ---------------------------------------------------------------------------
# CIRCLE — midpoint algorithm with aspect ratio, arcs, pie slices
# ---------------------------------------------------------------------------


def circle(
    cx: int,
    cy: int,
    radius: int,
    color: int = -1,
    start_angle: float = None,
    end_angle: float = None,
    aspect: float = None,
) -> None:
    """CIRCLE (cx, cy), radius[, color][, start][, end][, aspect].

    Angles in radians. 0 = 3 o'clock, positive = counterclockwise on screen
    (since screen y increases downward, but we use y = cy - r*sin(a)).

    Negative start or end angle → draw line from arc endpoint to center (pie slice).
    Aspect > 1: y-radius = radius, x-radius = radius/aspect.
    Aspect < 1: x-radius = radius, y-radius = radius * aspect.
    """
    if color < 0:
        color = 15
    
    # Clamp color to palette size (4 for CGA, 16 for EGA)
    max_color = 3 if scr.mode() == 1 else 15
    color = color & max_color

    if aspect is None:
        aspect = 1.0

    # Compute x and y radii from aspect ratio.
    if aspect >= 1.0:
        rx = max(1, int(round(radius / aspect)))
        ry = max(1, radius)
    else:
        rx = max(1, radius)
        ry = max(1, int(round(radius * aspect)))

    # Determine if we need pie-slice lines (negative angles).
    draw_line_start = False
    draw_line_end = False
    if start_angle is not None and start_angle < 0:
        draw_line_start = True
        start_angle = -start_angle
    if end_angle is not None and end_angle < 0:
        draw_line_end = True
        end_angle = -end_angle

    # Normalize angles.
    if start_angle is None:
        start_angle = 0.0
    if end_angle is None:
        end_angle = 2.0 * math.pi

    # Ensure start < end; if start > end, the arc wraps around.
    if end_angle < start_angle:
        end_angle += 2.0 * math.pi

    # Draw the ellipse/arc using parametric approach for accuracy.
    fb = scr.fb()
    h, w = fb.shape

    # Number of steps: proportional to circumference for smooth arcs.
    circumference = math.pi * (3 * (rx + ry) - math.sqrt((3 * rx + ry) * (rx + 3 * ry)))
    steps = max(64, int(circumference * 2))

    prev_px, prev_py = None, None
    start_pt = None
    end_pt = None

    for i in range(steps + 1):
        a = start_angle + (end_angle - start_angle) * i / steps
        px = int(round(cx + rx * math.cos(a)))
        py = int(round(cy - ry * math.sin(a)))

        if i == 0:
            start_pt = (px, py)
        if i == steps:
            end_pt = (px, py)

        # Connect consecutive points with a short line to avoid gaps.
        if prev_px is not None:
            _plot_line(prev_px, prev_py, px, py, color)
        prev_px, prev_py = px, py

    # Pie-slice lines: from arc endpoints to center.
    if draw_line_start and start_pt:
        _plot_line(start_pt[0], start_pt[1], cx, cy, color)
    if draw_line_end and end_pt:
        _plot_line(end_pt[0], end_pt[1], cx, cy, color)


# ---------------------------------------------------------------------------
# PAINT — flood fill
# ---------------------------------------------------------------------------


def paint(
    x: int,
    y: int,
    fill_color: int = -1,
    border_color: int = -1,
    tile_pattern: bytes = None,
) -> None:
    """PAINT (x, y)[, fill][, border][, tile].

    Flood fill from (x, y). Stops at pixels matching border_color.
    fill_color: color to fill with (-1 = current foreground).
    border_color: color of the boundary (-1 = fill_color).
    tile_pattern: optional tiling pattern (bytes, each byte = 8 pixels).
    """
    if fill_color < 0:
        fill_color = 15
    
    # Clamp colors to palette size (4 for CGA, 16 for EGA)
    max_color = 3 if scr.mode() == 1 else 15
    fill_color = fill_color & max_color

    if border_color < 0:
        # QBASIC default: border = fill color (not foreground).
        border_color = fill_color
    border_color = border_color & max_color

    fb = scr.fb()
    h, w = fb.shape

    if not (0 <= x < w and 0 <= y < h):
        return

    # Don't fill if starting pixel is the border color.
    if fb[y, x] == border_color:
        return

    # BFS flood fill.
    visited = np.zeros((h, w), dtype=bool)
    queue = deque()
    queue.append((x, y))
    visited[y, x] = True

    while queue:
        px, py = queue.popleft()

        # Determine fill value (with optional tile pattern).
        if tile_pattern:
            pat_row = py % len(tile_pattern)
            pat_byte = tile_pattern[pat_row]
            bit = 7 - (px % 8)
            fill_val = fill_color if (pat_byte >> bit) & 1 else 0
        else:
            fill_val = fill_color

        fb[py, px] = fill_val

        # Expand to 4-connected neighbors.
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = px + dx, py + dy
            if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx]:
                visited[ny, nx] = True
                if fb[ny, nx] != border_color:
                    queue.append((nx, ny))


# ---------------------------------------------------------------------------
# GET / PUT — sprite capture and blit
# ---------------------------------------------------------------------------


def get_sprite(x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    """GET (x0,y0)-(x1,y1) — capture a rectangular region of the framebuffer.

    Returns a numpy uint8 array of shape (h, w) with the pixel values.
    """
    fb = scr.fb()
    left = min(x0, x1)
    top = min(y0, y1)
    right = max(x0, x1)
    bot = max(y0, y1)
    return fb[top : bot + 1, left : right + 1].copy()


def put_sprite(
    x: int,
    y: int,
    sprite: np.ndarray,
    action: str = "XOR",
) -> None:
    """PUT (x, y), sprite[, action].

    Actions:
      PSET   — copy sprite pixels directly
      PRESET — copy complement of sprite pixels
      XOR    — XOR sprite with framebuffer (default; used for erase/redraw)
      AND    — AND sprite with framebuffer
      OR     — OR sprite with framebuffer
    """
    fb = scr.fb()
    h, w = fb.shape
    sh, sw = sprite.shape

    # Clip to framebuffer bounds.
    src_x0 = max(0, -x)
    src_y0 = max(0, -y)
    dst_x0 = max(0, x)
    dst_y0 = max(0, y)
    copy_w = min(sw - src_x0, w - dst_x0)
    copy_h = min(sh - src_y0, h - dst_y0)

    if copy_w <= 0 or copy_h <= 0:
        return

    src = sprite[src_y0 : src_y0 + copy_h, src_x0 : src_x0 + copy_w]
    dst = fb[dst_y0 : dst_y0 + copy_h, dst_x0 : dst_x0 + copy_w]

    if action == "PSET":
        dst[:] = src
    elif action == "PRESET":
        dst[:] = (~src) & 0x0F
    elif action == "XOR":
        dst[:] = dst ^ src
    elif action == "AND":
        dst[:] = dst & src
    elif action == "OR":
        dst[:] = dst | src
    else:
        raise ValueError(f"Unknown PUT action: {action}")


# ---------------------------------------------------------------------------
# Banana sprite DATA decoding (QBASIC GET/PUT array format)
# ---------------------------------------------------------------------------


def decode_put_data(longs: list, bpp: int = 4) -> np.ndarray:
    """Decode a QBASIC GET/PUT long-array into a 2D pixel array.

    Args:
        longs: list of 32-bit integers (as read from DATA).
        bpp: bits per pixel (4 for EGA/SCREEN 9, 2 for CGA/SCREEN 1).

    The first long contains the header: low 16 bits = width in pixels,
    high 16 bits = height in pixels (little-endian word order).

    Returns a numpy uint8 array of shape (h, w) with pixel values 0..15 (EGA)
    or 0..3 (CGA).

    Note: the exact EGA planar layout has word-aligned rows. We try both
    byte-aligned and word-aligned and pick the one that produces valid data.
    """
    import struct

    if not longs:
        return np.zeros((1, 1), dtype=np.uint8)

    # Decode header from first long.
    header = longs[0] & 0xFFFFFFFF
    # Little-endian: first word (bits 0-15) = width, second word (bits 16-31) = height.
    w_pixels = header & 0xFFFF
    h_pixels = (header >> 16) & 0xFFFF

    if w_pixels == 0 or h_pixels == 0:
        return np.zeros((max(1, h_pixels), max(1, w_pixels)), dtype=np.uint8)

    data_longs = longs[1:]

    # Convert remaining longs to bytes (little-endian).
    data_bytes = b""
    for val in data_longs:
        data_bytes += struct.pack("<I", val & 0xFFFFFFFF)

    if bpp == 4:
        # EGA: 4 bit planes, each plane has ceil(w/8) bytes per row.
        # Try byte-aligned first.
        bytes_per_plane_row = (w_pixels + 7) // 8
        expected = 4 * bytes_per_plane_row * h_pixels

        if len(data_bytes) >= expected:
            pixels = np.zeros((h_pixels, w_pixels), dtype=np.uint8)
            offset = 0
            for row in range(h_pixels):
                for plane in range(4):
                    for byte_idx in range(bytes_per_plane_row):
                        if offset >= len(data_bytes):
                            break
                        b = data_bytes[offset]
                        offset += 1
                        for bit in range(8):
                            col = byte_idx * 8 + (7 - bit)
                            if col < w_pixels:
                                if (b >> bit) & 1:
                                    pixels[row, col] |= 1 << plane
            return pixels
        else:
            # Try word-aligned (2 bytes per plane per row).
            bytes_per_plane_row = 2
            expected = 4 * bytes_per_plane_row * h_pixels
            pixels = np.zeros((h_pixels, w_pixels), dtype=np.uint8)
            offset = 0
            for row in range(h_pixels):
                for plane in range(4):
                    for byte_idx in range(bytes_per_plane_row):
                        if offset >= len(data_bytes):
                            break
                        b = data_bytes[offset]
                        offset += 1
                        for bit in range(8):
                            col = byte_idx * 8 + (7 - bit)
                            if col < w_pixels:
                                if (b >> bit) & 1:
                                    pixels[row, col] |= 1 << plane
            return pixels

    elif bpp == 2:
        # CGA: 2 bit planes, each plane has ceil(w/8) bytes per row.
        bytes_per_plane_row = (w_pixels + 7) // 8
        pixels = np.zeros((h_pixels, w_pixels), dtype=np.uint8)
        offset = 0
        for row in range(h_pixels):
            for plane in range(2):
                for byte_idx in range(bytes_per_plane_row):
                    if offset >= len(data_bytes):
                        break
                    b = data_bytes[offset]
                    offset += 1
                    for bit in range(8):
                        col = byte_idx * 8 + (7 - bit)
                        if col < w_pixels:
                            if (b >> bit) & 1:
                                pixels[row, col] |= 1 << plane
        return pixels

    else:
        raise ValueError(f"Unsupported bpp: {bpp}")
