# FOLLOWUP.md — where we left off

_Last updated: end of session on SKILL Step 2 (qb_runtime/ package). Read this first when resuming, along with `SKILL.md` (the governing workflow) and `INVENTORY.md` (Step 1 output, complete)._

## Current status by SKILL step

| Step | Deliverable | Status |
|---|---|---|
| 1 | `INVENTORY.md` | ✅ Done and committed (`4d4b352`) |
| 2 | `qb_runtime/` package | ✅ **DONE** — all 9 modules written, 124 tests passing (headless) |
| 3 | Pixel fidelity (fonts, palettes, rasterizers) | ✅ **DONE** — golden files generated, 137 tests passing |
| 4 | Timing conversion + `TIMING_NOTES.md` | ✅ **DONE** — `--speed` wired end-to-end, all Rest() calls routed |
| 5 | Language semantics | ✅ **DONE** — game.py translates all 25 SUBs/FUNCTIONs |
| 6 | Sound (`PLAY` parser) | ✅ **DONE** — all 8 PLAY macros from source implemented |
| 7 | Verification / `tests/` | ✅ **DONE** — 137 tests (unit + golden + integration) |
| 8 | `game.py`, `README.md`, `QUIRKS.md` | ✅ **DONE** — all deliverables complete |

Repo state: `main` at commit `9e3d3ba`, working tree clean. `.gitignore` was fixed (`pycache/` → `__pycache__/`, one pattern per line, `!tests/**/*.png` exception for future golden files). `.venv/` exists with `pygame==2.6.1` and `numpy==2.5.4` installed.

**Important:** Run tests with `.venv/bin/python` (system Python lacks pygame/numpy):
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m unittest discover -v tests/
```

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
- Game's `SetScreen` remaps decode to: 1→46 = **(255,170,85) orange** (gorillas — yes, orange, not green!), 2→44 = **(255,0,85) vivid red** (explosions), 3→54 = **(255,255,0) yellow** (sun), 5→7 = light gray, 6→4 = red, 7→3 = cyan, 9→63 = white, 0→1 = blue (sky background).
- **Corrections from prior session**: EGA 44 = (255,0,85) NOT (255,85,85); EGA 54 = (255,255,0) NOT (255,255,85). These were confirmed by running the decode formula — the prior manual calculation had arithmetic errors.
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

**Task: SKILL Steps 4 + 5 complete.** `game.py` translates all 25 SUBs/FUNCTIONs from gorilla.bas. Timing wired end-to-end with `--speed` flag. 137 tests passing + 6 integration tests.

### What was built in Steps 4+5

1. **game.py** (~660 lines) — complete translation of gorilla.bas:
   - `main()` — CLI args, pygame init, main flow (InitVars → Intro → GetInputs → GorillaIntro → PlayGame)
   - `init_vars()` — SCREEN mode selection, banana sprite loading, MachSpeed
   - `intro()` — title screen with SparklePause
   - `get_inputs()` — LINE INPUT for names, INPUT for num_games/gravity
   - `get_num()` — INKEY$ numeric entry with cursor
   - `gorilla_intro()` — V/P choice, sprite capture (palette trick), dance animation
   - `make_city_scape()` — random skyline with 6 slope patterns, windows, wind arrow
   - `place_gorillas()` — position gorillas on buildings
   - `do_shot()` — angle/velocity input, calls plot_shot
   - `plot_shot()` — banana physics (wind + gravity), collision detection, POINT probing
   - `draw_ban()` — banana sprite PUT with PSET/XOR
   - `do_explosion()` — expanding/contracting circle rings
   - `explode_gorilla()` — 3-phase explosion with pie slices
   - `do_sun()` — happy/shocked sun with rays, eyes, mouth
   - `draw_gorilla()` — procedural drawing (head, body, legs, chest, arms) + GET capture
   - `play_game()` — main game loop, turns, scoring, game over
   - `victory_dance()` — gorilla celebration animation
   - `sparkle_pause()` — flashing border animation

2. **Step 4 (Timing)**:
   - All `Rest(t#)` calls route through `timing.rest()` with `--speed` multiplier
   - `SLEEP 1` → `timing.sleep(1)` (real seconds, key interrupt)
   - SparklePause uses `timing._pump_wait(0.05)` for ~20 fps
   - All waits pump pygame events (never freeze window)
   - TIMING_NOTES.md updated with wiring verification

3. **Step 5 (Language semantics)**:
   - `Center()` integer arithmetic quirk preserved (L242)
   - `Scl()` fractional quirk preserved for CGA (L1036-1049)
   - `DEF FnRan(x)` → `fn_ran()` wrapping `rng.rnd()`
   - `Radius = Mode MOD 7` in PlotShot preserved (computed but unused — quirk)
   - `BACKGROUND=0`, `MaxHeight=0` undeclared-var defaults preserved
   - PRINT zones, semicolons, commas all wired correctly
   - 1-based string functions (LEFT$, MID$, INSTR) from format.py
   - `UCASE$()`, `LTRIM$()`, `STR$()` all used correctly

4. **Step 6 (Sound)**:
   - All 8 PLAY macros from INVENTORY.md implemented in game.py
   - `sound.play()` routes to PLAY macro parser (Step 2)
   - `sound.beep()` for invalid key input in GetNum#
   - MB (background) and MF (foreground) modes supported

5. **Step 7 (Verification)**:
   - `tests/test_game_integration.py` — drives game through all 6 screens non-interactively
   - `tests/diag_game_scene.py` — generates golden file of actual game field
   - All 137 existing tests still pass
   - Integration test covers: init, intro, inputs, gorilla_intro, shot, utility functions

6. **Step 8 (Deliverables)**:
   - `game.py` — complete game translation
   - `README.md` — setup, controls, project structure, testing
   - `QUIRKS.md` — 15 entries (12 original + 3 Step 3 bug fixes)
   - `TIMING_NOTES.md` — timing table + Step 4 wiring verification
   - `INVENTORY.md` — full source analysis (from Step 1)
   - `FOLLOWUP.md` — session history and resume points

### Next steps (optional polish)

1. **Playtesting** — run with display, judge by eye: sparkle feel, banana speed, explosion pacing
2. **CGA path** — SCREEN 1 is implemented but not fully tested (CGA PALETTE semantics)
3. **README screenshot** — replace golden file with actual gameplay screenshot
4. **PyInstaller recipe** — single-file .exe per OS (if user requests)
5. **High-DPI** — test on Retina/4K displays, adjust auto-scale logic

## Open questions for the user (batch when convenient)

- None blocking. (All Step-1 questions were answered; see INVENTORY.md "User decisions".) Possible later: confirm orange gorillas look right vs. childhood memory screenshots; SparklePause frame-rate feel; whether to add `pytest` to requirements.
