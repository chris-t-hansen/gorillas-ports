# QWEN.md

## Project Overview

**gorillas-ports** is a preservation-port project whose goal is to convert the classic DOS-era QBASIC game **GORILLA.BAS** (Microsoft, 1990) into a modern, standalone Python program that looks, sounds, and behaves like the original — without DOSBox or any emulator.

The repository currently contains only the source material and the conversion methodology; **no port code exists yet**:

- `gorilla.bas` — the original QBASIC source (1,136 lines), the program to be ported
- `SKILL.md` — a detailed skill/workflow document ("qbasic-to-python-retro") defining how the conversion must be done
- `LICENSE` — MIT, Copyright (c) 2026 Chris Hansen

GORILLA.BAS is the two-player artillery game where gorillas on a randomly generated city skyline throw exploding bananas at each other, adjusting angle and velocity for wind and gravity.

## Key Facts About `gorilla.bas`

Any port must account for these constructs found in the source:

- **Global typing:** `DEFINT A-Z` at the top; `#` (double) and `!` (single) suffixes used where precision matters; `$DYNAMIC` is commented out.
- **Screen modes:** tries `SCREEN 9` (EGA 640x350) first, falls back to `SCREEN 1` (CGA 320x200) via `ON ERROR GOTO ScreenModeError` / `RESUME`. A `PALETTE 4, 0` probe detects 64K EGA cards (`PaletteError:` → CGA mode via `RESUME NEXT`). Intro screens use `SCREEN 0`.
- **Palette remapping:** `SetScreen` reassigns EGA palette entries (`PALETTE 0,1`, `PALETTE 1,46`, etc.). Rendering must use an indexed-color framebuffer with the palette applied at present time.
- **Sprites:** banana and gorilla bitmaps stored as QBASIC `GET/PUT` LONG-array `DATA` statements with separate `CGABanana:` and `EGABanana:` blocks, loaded via `RESTORE`/`READ` into `LBan&/RBan&/UBan&/DBan&` and `GorL&/GorD&/GorR&`. `PUT ... PSET` and `PUT ... XOR` are both used (XOR for animated banana flight).
- **Graphics:** heavy use of `CIRCLE` (with arc angles and aspect parameter `-1.57`), `PAINT`, `LINE`, `GET`, `PUT`, and a `Scl()` function that halves coordinates in CGA mode (with a quirk: fractional inputs are scaled down by 1 first in Mode 1).
- **Timing (CPU-speed dependent — critical for the port):**
  - `CONST SPEEDCONST = 500` is the documented game-speed knob.
  - `CalcDelay!` busy-loops against `TIMER` for 0.5 s to measure machine speed into `MachSpeed` (multiplied by 1.3 in CGA mode).
  - `Rest(t#)` waits `MachSpeed * t# / SPEEDCONST` seconds using a `TIMER` busy-wait — all `Rest` calls throughout the game route through this.
  - `RANDOMIZE TIMER` per game; `SLEEP 1` used in `PlayGame`.
- **Sound:** `PLAY` music macro strings (both `MF` foreground and `MB` background), e.g. the intro theme, explosion jingles, and the victory-dance loop.
- **Input:** `LINE INPUT`/`INPUT` for names, score limit, gravity; `INKEY$` polling in `GetNum#`/`Getn#` (digit-by-digit angle/velocity entry with backspace handling), `SparklePause`, and the shot loop.
- **Low-level hardware:** `DEF SEG = 0` with `PEEK/POKE 1047` (`&H417` keyboard flags) to force NumLock ON at startup and restore it at exit.
- **Error handling:** `ON ERROR GOTO` + `RESUME`/`RESUME NEXT` for mode and palette probing.
- **Structure:** one main flow (`InitVars` GOSUB → `Intro` → `GetInputs` → `GorillaIntro` → `PlayGame`) plus 25 `DECLARE`d SUBs/FUNCTIONs defined after `END`. Labels used as data anchors (`CGABanana:`, `EGABanana:`, `InitVars:`) and error targets.

## SKILL.md — The Conversion Workflow (authoritative)

`SKILL.md` is the governing document for the port. Follow it step by step; its requirements include:

1. **Preservation, not modernization:** keep all behavior, text, layout, colors, and original bugs; record deviations in `QUIRKS.md`. Comment each translated block with its source reference (`# BAS line 142-158`).
2. **Step 1 — Inventory:** read the whole `.BAS` and produce `INVENTORY.md` (screen modes, colors, graphics/sound/input/timing/low-level constructs).
3. **Step 2 — Runtime layer:** build a `qb_runtime/` package (`screen.py`, `text.py`, `graphics.py`, `keyboard.py`, `sound.py`, `timing.py`, `rng.py`, `files.py`, `format.py`) so `game.py` reads almost line-for-line like the original.
4. **Step 3 — Pixel fidelity:** pygame, native-resolution offscreen surface, integer nearest-neighbor scaling; Code Page 437 with a real IBM VGA bitmap font (Px437 pack); exact 16-color text palette; custom rasterizers for `CIRCLE`/`PAINT` (do not trust pygame's built-ins); indexed framebuffer for live `PALETTE` changes; 4:3 presentation for 320x200 modes.
5. **Step 4 — Kill CPU-speed dependence:** replace `CalcDelay`/`Rest`/busy-waits with wall-clock time; all timing constants in one documented table; every conversion logged in `TIMING_NOTES.md` (source line | loop count | assumption | seconds | confidence); never block the window without pumping events.
6. **Step 5 — Language semantics:** 16-bit INTEGER overflow, single-precision formatting (`qb_str`), `\` / `MOD` / `INT` / `FIX` / `CINT` (banker's rounding), 1-based string functions, `INPUT` prompts (`? `, `Redo from start`), `INKEY$` two-byte extended-key codes, QBASIC's LCG for `RND` if exact sequences matter.
7. **Step 6 — Sound:** numpy square waves via `pygame.mixer` (harsh PC-speaker timbre), full `PLAY` macro parser, `--mute` flag.
8. **Step 7 — Verification:** run every screen; golden-file tests of the 80x25 text grid and framebuffer PNGs; unit-test formatting/rounding helpers; verify delays within ~5%; no 100% CPU idle loops.
9. **Step 8 — Deliverables:** `game.py`, `qb_runtime/`, pinned `requirements.txt`, `README.md` (venv setup, controls, flags `--scale`, `--mute`, `--fullscreen`, `--speed`), `TIMING_NOTES.md`, `QUIRKS.md`, `INVENTORY.md`, `tests/`.

SKILL.md also lists **questions to ask the user up front** (original hardware era, interpreted vs compiled, CPU speed/feel, window scaling preference, pixel aspect ratio, whether exact `RND` sequences matter). Ask these in a single message before starting the port.

## Building and Running

- **Original program:** requires a DOS-era QBASIC interpreter (e.g., QBASIC 1.1 / DOSBox). It is reference material only — never shipped as part of the final product.
- **Python port (planned):** no port exists yet. When it does, the expected workflow per SKILL.md is:

  ```bash
  python -m venv .venv
  source .venv/bin/activate        # Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  python game.py
  ```

- **Tests (planned):** `tests/` directory with golden-file and unit tests, per SKILL.md Step 7. No test runner is configured yet — TODO: establish one (e.g., `pytest`) when the port begins.

## Development Conventions

- **Follow SKILL.md strictly.** It is the project's specification; report progress by its step numbers.
- **Do not "improve" the game.** Preserve quirks (e.g., the `Scl()` fractional-coordinate quirk, the NumLock POKE, `UpdateScores`'s `ABS(PlayerNum - 3)` self-hit scoring) and document them in `QUIRKS.md`.
- **Traceability:** every translated block carries a comment citing its `.BAS` line range or SUB/FUNCTION name.
- **Timing decisions are data, not code:** all delay/speed constants live in one configurable table, with assumptions and confidence levels recorded in `TIMING_NOTES.md`.
- **Ambiguity → ask the user** (batched into one message) rather than guessing; especially for intended delays, screen-mode/era choices, and `RND` determinism.
- **Standard library first;** pip dependencies (expected: `pygame`, `numpy`) must be pinned in `requirements.txt`.
- **Licensing note:** `SKILL.md` requires shipping a bitmap font (e.g., Px437 IBM VGA from The Ultimate Oldschool PC Font Pack) with its license included under `assets/fonts/`. The original GORILLA.BAS is © Microsoft 1990; this repo's LICENSE (MIT) covers the port work.
