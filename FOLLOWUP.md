# FOLLOWUP.md — where we left off

_Last updated: end of session on SKILL Step 2 (qb_runtime/ package). Read this first when resuming, along with `SKILL.md` (the governing workflow) and `INVENTORY.md` (Step 1 output, complete)._

## Current status by SKILL step

| Step | Deliverable | Status |
|---|---|---|
| 1 | `INVENTORY.md` | ✅ Done and committed (`4d4b352`) |
| 2 | `qb_runtime/` package | 🔶 **IN PROGRESS — research done, no code written yet** |
| 3 | Pixel fidelity (fonts, palettes, rasterizers) | ❌ not started |
| 4 | Timing conversion + `TIMING_NOTES.md` | ❌ not started |
| 5 | Language semantics | ❌ not started |
| 6 | Sound (`PLAY` parser) | ❌ not started |
| 7 | Verification / `tests/` | ❌ not started |
| 8 | `game.py`, `README.md`, `QUIRKS.md` | ❌ not started |

Repo state: `main` pushed to `origin` (`github.com/chris-t-hansen/gorillas-ports`), working tree clean. `.gitignore` was fixed (`pycache/` → `__pycache__/`, one pattern per line, `!tests/**/*.png` exception for future golden files). `.venv/` exists with `pygame==2.6.1` and `numpy==2.5.4` installed.

**Commit message convention (user request):** credit `qwen3.8-max` in every commit message, e.g. trailer `Written by qwen3.8-max` (matches style of older `d2f2353` commit).

## Research findings from this session (verified — do not redo blindly)

### 1. Font loading works (tested headless with `SDL_VIDEODRIVER=dummy`)

`pygame.font.Font("assets/fonts/Bm437_IBM_EGA_8x14.otb", 14)` loads and renders **pixel-perfect**:

- Rendered surface is **8x16** (ascent 13, descent -3); the actual 8x14 cell content sits at **rows 2..15** of that surface (verified with U+2588 full-block glyph). So blit glyph surfaces at `(col*8, row*14 - 2)` for the EGA 8x14 font. Better: compute this offset dynamically at load time from the full-block glyph (don't hardcode).
- CP437 → Unicode conversion works via `bytes([c]).decode("cp437")` (smiley 0x01 → U+263A renders correctly).
- The `.otb` files are the Px437 pack fonts (EGA 8x14, VGA 8x14, VGA 9x16, CGA 8x8), license in `assets/fonts/LICENSE.TXT`.

### 2. EGA 6-bit palette encoding SOLVED (for `PALETTE n, value` in SCREEN 9)

Bit layout of the 6-bit EGA color value `v` is **`[Sr Sg Sb | R G B]`** = `[b5 b4 b3 | b2 b1 b0]`, where uppercase bits are "secondary" (add 0x55) and lowercase are "primary" (add 0xAA):

```python
r = 0xAA * ((v >> 2) & 1) + 0x55 * ((v >> 5) & 1)
g = 0xAA * ((v >> 1) & 1) + 0x55 * ((v >> 4) & 1)
b = 0xAA * ( v       & 1) + 0x55 * ((v >> 3) & 1)
```

Verified against every known anchor: 1→(0,0,170) blue, 4→(170,0,0) red, 7→(170,170,170) light gray, 20→(170,85,0) **brown**, 56→(85,85,85) dark gray, 63→white.

- SCREEN 9 **default palette registers** (attr 0–15): `[0, 1, 2, 3, 4, 5, 20, 7, 56, 57, 58, 59, 60, 61, 62, 63]` (note brown=20, NOT 6).
- Game's `SetScreen` remaps decode to: 1→46 = **(255,170,85) orange** (gorillas — yes, orange, not green!), 2→44 = (255,85,85) red (explosions), 3→54 = (255,255,85) pale yellow (sun), 5→7 = light gray, 6→4 = red, 7→3 = cyan, 9→63 = white, 0→1 = blue (sky background).
- 16-color **text palette** for SCREEN 0 is the standard CGA/VGA set from SKILL.md (`#000000 #0000AA #00AA00 #00AAAA #AA0000 #AA00AA #AA5500 #AAAAAA #555555 #5555FF #55FF55 #55FFFF #FF5555 #FF55FF #FFFF55 #FFFFFF`).

### 3. Timing model derived (goes in `timing.py` + `TIMING_NOTES.md`)

Source facts: `CalcDelay!` (BAS L228-236) counts `DO: i! = i! + 1: LOOP UNTIL TIMER - s! >= .5` → counts-per-0.5s. `MachSpeed = CalcDelay` (L156), ×1.3 in CGA mode (L205). `Rest(t#)` (L1024-1031) busy-waits `MachSpeed * t# / SPEEDCONST` seconds, `SPEEDCONST = 500`.

**Conclusion: the design intent is `Rest(t#) ≈ t# seconds` on the author's reference machine** (MachSpeed ≈ SPEEDCONST = 500 there; the interpreted loop with a TIMER call per iteration is slow, ~1000 iter/s). So the port maps `Rest(t#)` → wall-clock wait of `t# / speed_multiplier` seconds. Confidence: medium — document in TIMING_NOTES.md, expose `--speed`. (User already decided: estimate from interpreter speed, document assumptions, `--speed` flag.)

- `TIMER` = seconds since local midnight, ~55 ms resolution; implement via real local time; midnight rollover quirk behaves like the original (document).
- Other timing items from INVENTORY: `SLEEP 1` per round; SparklePause is CPU-paced (pick ~10 fps, document); empty loops `FOR i=1 TO 100` (DoExplosion) / `FOR Count=1 TO 200` (ExplodeGorilla) → negligible, map to ~0.
- All waits must pump pygame events + present, never busy-wait, never freeze the window (SKILL Step 4 rules 9-10).

### 4. Banana sprite DATA format (partially decoded — finish in Step 3)

`CGABanana:` (L125-133) = 4 directions × 3 LONGs (12 bytes: 4-byte header + 8 bytes data); `EGABanana:` (L135-143) = 4 directions × 9 LONGs (36 bytes: header + 32 bytes data). ✅ Verified: all 4 EGA directions present including BananaRight (L142-143).

Header interpretation (QBASIC GET/PUT format): first 4 bytes = width (16-bit), height (16-bit) in pixels. Decoded headers:
- CGA BananaLeft: 327686 = 0x0005_0006 → **w=6? h=5?** (check endianness: low word first → width=6, height=5? Actually 327686 = 0x50006: word0=0x0006 (w=6), word1=0x0005 (h=5)). CGA BananaDown: 196618 = 0x3000A → w=10 (0xA), h=3.
- EGA BananaLeft: 458758 = 0x70006 → w=6, h=7. EGA BananaDown: 262153 = 0x40009 → w=9, h=4.

Data bytes per scanline: SCREEN 1 (2bpp): ceil(w*2/8) per plane × 2 planes? SCREEN 9 (4bpp planar): 4 planes × ceil(w/8) bytes/row, possibly word-aligned. Verify: EGA w=6,h=7 → 4 planes × 1 byte × 7 rows = 28 ≠ 32 → maybe word-aligned rows (2 bytes/plane/row → 4×2×7=56 ≠ 32) → **layout needs empirical decoding** (dump bits and match expected banana shape). CGA w=6,h=5: 2 planes × 1 byte × 5 = 10 ≠ 8; w=10,h=3: 2 planes × 2 bytes × 3 = 12 ≠ 8 → header word order may be swapped (w/h flipped) — try both. **This is the first task in Step 3 sprite work.**

Gorilla sprites are NOT in DATA — captured at runtime via `GET` in DrawGorilla; the port can draw procedurally and capture from its own framebuffer (same code path as QBASIC).

### 5. Design decisions made for qb_runtime (agreed in-session, not yet coded)

- Single-window pygame app; **native-resolution indexed framebuffer** as `numpy uint8` (H,W); palette (16 entries → RGB) applied **at present time only** (SKILL Step 3 requirement).
- **EGA-era geometry chosen for consistency**: SCREEN 0 → 640x350 with 8x14 font (matches SCREEN 9 so mode switches are seamless); SCREEN 1 → 320x200 with 8x8 CGA font, WIDTH 40; SCREEN 9 → 640x350. Document in QUIRKS/README (VGA 720x400 SCREEN 0 rejected for consistency).
- Presentation: 4:3 window, letterboxed, nearest-neighbor scaling; `--scale N` for integer square-pixel scaling, `--fullscreen`. (Fine-tuning in Step 3.)
- Text: parallel text grid (chars + attrs) for state/scroll/VIEW PRINT/golden tests; glyph blits written **directly into the framebuffer** as printed (graphics pages aren't a text layer); full redraw = bg fill + all cells.
- `INKEY$` mapping: Enter=chr(13), Esc=chr(27), Backspace=chr(8), Tab=chr(9), arrows=chr(0)+chr(72/80/75/77); OS key-repeat (documented choice).
- CGA (SCREEN 1) is the **secondary path** per user decision — implement but EGA is primary.
- RND: user said exact sequences NOT required → wrap Python `random` (still provide `rnd()`/`randomize()` API; QBASIC LCG optional later).
- `files.py` from the SKILL layout is **not needed** (game has no file I/O) — note in QUIRKS.md when created.
- Module APIs planned: `screen.py` (init/screen/width/palette/cls/view_print/point/pump/present/fb), `text.py` (print_ with S/C separator sentinels + TAB()/SPC(), locate, color, cursor, blink ~1.875 Hz), `graphics.py` (pset/line with 16-bit style/circle with arcs+negative-aspect pie/point/paint flood+pattern/get_sprite/put_sprite with PSET/XOR/AND/OR/PRESET + `decode_put_data` for DATA bananas), `keyboard.py` (inkey/flush/input_str with `? ` + `Redo from start`/wait_key), `sound.py` (PLAY macro parser: M B/F/N/L/S, O, L, T, V, N, P, A-G # + -, durations, dots; square waves via numpy+pygame.mixer; MF blocks (pumping events), MB background thread; BEEP 800 Hz 0.25 s; `--mute`), `timing.py` (timer/wait/sleep_qb/rest + TIMING_TABLE with BAS line citations + `--speed`), `rng.py`, `qbmath.py` (cint banker's rounding, int_/fix_, idiv, mod_, int16 overflow, sng float32), `format.py` (qb_str/STR$/VAL/1-based LEFT$/MID$/RIGHT$/INSTR/SPACE$/STRING$/UCASE$/etc.).
- Negative CIRCLE aspect = pie-slice (lines from arc endpoints to center) — used by ExplodeGorilla (`-1.57`). Angles: 0 = 3 o'clock, increase counterclockwise on screen (y = cy − r·sin(a)). Write own rasterizers (no pygame.draw.circle).
- Aspect > 1: y-radius = radius, x-radius = radius/aspect; aspect < 1: x-radius = radius, y-radius = radius·aspect.
- SCREEN 1 colors wrap mod 4 (window color 6 → 2); CGA PALETTE 0=bg color (0-15), PALETTE 1=palette select (bit4 palette 0/1, bit5 intensity); note GorillaIntro's `PALETTE 1,46` on CGA is a quirk → document.
- SCREEN 1 `COLOR 0, 2` (SetScreen): foreground/palette semantics per QBASIC SCREEN 1 rules.
- Text `PRINT` numeric formatting: leading space (or `-`), trailing space; `qb_str` for single (7 digits) and double; exponential forms like QBASIC (`1E+07`); `.5` not `0.5`.
- PRINT zones: comma → next 14-column zone (cols 1,15,29,43,57,71); trailing `;` suppresses newline; TAB(n)/SPC(n) 1-based.
- `Center()` integer-arithmetic quirk and `Scl()` fractional quirk live in **game.py** (game-level), not runtime.
- Undeclared-var defaults (`BACKGROUND`=0, `MaxHeight`=0) preserved as 0 in game.py.
- NumLock PEEK/POKE 1047 → no-op, document in QUIRKS.md.
- Dead declares `EndGame`/`Getn#` → dropped, document in QUIRKS.md.

## Exact resume point

**Task: write the `qb_runtime/` package (SKILL Step 2).** Nothing has been coded yet — the session ended right after the research above (last action was reading banana DATA lines L125-141 and DrawBan L370-400 from `gorilla.bas`).

Suggested order of work tomorrow:

1. `qb_runtime/qbmath.py` + `format.py` (pure logic, easy to unit test) → `tests/` with `unittest` (stdlib; pytest not yet in requirements — decide whether to add it).
2. `screen.py` (framebuffer, palettes incl. EGA-64 decode above, window/scaling, pump/present).
3. `font` handling + `text.py` (grid, print/locate/color/scroll/VIEW PRINT, cursor, blink).
4. `graphics.py` (pset/line/circle/paint/point/get/put).
5. `keyboard.py`, `timing.py`, `rng.py`, `sound.py`.
6. Headless smoke test (`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`) exercising SCREEN 0/9/1, PRINT, LINE, CIRCLE, palette remap, PLAY parsing.
7. Commit with `Written by qwen3.8-max` trailer; start `QUIRKS.md`/`TIMING_NOTES.md` skeletons as decisions get recorded.

Then Step 3: sprite DATA decoding (finish layout analysis from finding #4), pixel-fidelity passes, golden-file tests.

## Open questions for the user (batch when convenient)

- None blocking. (All Step-1 questions were answered; see INVENTORY.md "User decisions".) Possible later: confirm orange gorillas look right vs. childhood memory screenshots; SparklePause frame-rate feel; whether to add `pytest` to requirements.
