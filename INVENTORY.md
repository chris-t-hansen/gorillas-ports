# INVENTORY.md — gorilla.bas source inventory (SKILL.md Step 1)

Source: `gorilla.bas`, 1,136 lines, Microsoft QBasic GORILLA.BAS (1990).
Line references are to the original file.

## User decisions (collected up front)

| Question | Decision |
|---|---|
| Graphics era | **EGA/VGA path primary** (SCREEN 9, 640x350); CGA path (SCREEN 1) implemented but secondary |
| Speed calibration | User never played it / doesn't remember → **estimate from interpreter speed**, document every assumption in `TIMING_NOTES.md`, expose `--speed` multiplier |
| Window | **Resizable, 4:3 aspect**, letterboxed, integer-scale default; flags `--scale`, `--fullscreen` |
| RND determinism | **Not required** — seed from time like `RANDOMIZE TIMER`; Python RNG acceptable |

## Program structure

Main flow (L110-123): NumLock POKE → `GOSUB InitVars` → `Intro` → `GetInputs` → `GorillaIntro` → `PlayGame` → restore NumLock → `END`.

25 DECLAREs (L25-49); definitions at L228-1136.
**`EndGame` (L27) and `Getn#` (L47) are declared but never defined and never called** — dead declarations, drop from port (note in QUIRKS.md).

Labels: `CGABanana:` / `EGABanana:` (DATA anchors, L125-141), `InitVars:` (GOSUB target, L142), `ScreenModeError:` / `PaletteError:` (error targets, L213/221).

## Typing and constants

- `DEFINT A-Z` (L23) — all unsuffixed vars are 16-bit INTEGER.
- `#` suffix (double): `pi#`, `gravity#`, `x#/y#/t#/c#/Inc#`, Angle#, InitXVel#, InitYVel#, MachSpeed is `AS SINGLE`.
- `!` suffix (single): `CalcDelay!`, `Scl(n!)`, `s!`, `i!` in CalcDelay.
- `&` suffix (long): sprite arrays `LBan& RBan& UBan& DBan& GorD&(120) GorL&(120) GorR&(120)`.
- `$DYNAMIC` commented out (L51) but arrays are REDIMed in InitVars.
- `TYPE XYPoint` (XCoor/YCoor AS INTEGER), used for `BCoor(0 TO 30)` building coordinates.
- Constants (L60-71): `SPEEDCONST = 500`, `TRUE = -1`, `FALSE = NOT TRUE`, `HITSELF = 1`, `BACKATTR = 0`, `OBJECTCOLOR = 1`, `WINDOWCOLOR = 14`, `SUNATTR = 3`, `SUNHAPPY = FALSE`, `SUNSHOCK = TRUE`, `RIGHTUP = 1`, `LEFTUP = 2`, `ARMSDOWN = 3`.
- `DEF FnRan(x) = INT(RND(1) * x) + 1` (L110).
- **Undeclared variables that default to 0**: `BACKGROUND` (L763, used as LINE color) and `MaxHeight` (L758) — both rely on DEFINT default 0. Preserve semantics (0).

## Screen modes

| Use | Where | Notes |
|---|---|---|
| `SCREEN 9` (EGA 640x350, 16/64) | tried first, L147-148 | `PALETTE 4, 0` probe for 64K-EGA (L153); on failure → `PaletteError:` sets `Mode = 1`, `RESUME NEXT` |
| `SCREEN 1` (CGA 320x200, 4 colors) | fallback via `ScreenModeError:` (L213-222) | `Mode = 1: RESUME`; if Mode 1 itself fails → message at row 10 col 5: "Sorry, you must have CGA, EGA color, or VGA graphics to play GORILLA.BAS" + `END` |
| `SCREEN Mode` | L151, GorillaIntro L597 | re-enter graphics mode |
| `SCREEN 0` + `WIDTH 80, 25` | Intro L663-664, PlayGame end L879-880 | text screens: title intro, GetInputs, game-over |
| `MaxCol` | 80 (Mode 9 / SCREEN 0), 40 (Mode 1, L686) | used by `Center` and name placement |

## COLOR / PALETTE usage

- `SetScreen` (L1051-1073): Mode 9 → `ExplosionColor=2, BackColor=1` + palette remap: `PALETTE 0,1 / 1,46 / 2,44 / 3,54 / 5,7 / 6,4 / 7,3 / 9,63`. Mode 1 → `ExplosionColor=2, BackColor=0`, `COLOR 0, 2` (black on green).
- `GorillaIntro` (L604, L614): `PALETTE OBJECTCOLOR, BackColor` (hide gorilla while capturing sprites) then `PALETTE OBJECTCOLOR, 46`.
- Text screens: `COLOR 15, 0` (Intro L666), `COLOR 7, 0` (GetInputs L492, game over L881, L893), `COLOR 4, 0` (SparklePause L1078).
- Building colors: Mode 9 → `FnRan(3) + 4` (colors 4-6 → remapped by palette to red/magenta/brown-ish); Mode 1 → 2.
- Window colors: Mode 1 → `(FnRan(2) - 2) * -3` (3 or 6); Mode 9 → `8` if `FnRan(4) = 1` else `WINDOWCOLOR` (14).

## Graphics statements

- `LINE`: buildings (`B`, `BF`), sun rays, gorilla body parts, wind arrow, explosion stripes.
- `CIRCLE`: sun body, gorilla arcs (with start/end angles in radians and **aspect `-1.57`** in ExplodeGorilla), explosion rings, eyes (radius 1).
- `PAINT`: sun fill `(x,y), SUNATTR`; "O" mouth `(x, y+Scl(5)), 0, 0` (border color 0).
- `PSET`: sun eye centers, gorilla nose (Mode 9 only).
- `POINT`: shot collision probe in PlotShot (L975) — returns palette index; compared against 0, `SUNATTR`, `OBJECTCOLOR`.
- `GET`: gorilla sprite capture `GET (x-Scl(15), y-Scl(1))-(x+Scl(14), y+Scl(28))` → 30x30 region (EGA) into `GorL&/GorR&/GorD&`.
- `PUT ... PSET`: gorillas, static bananas. `PUT ... XOR`: banana erase/animation (DrawBan, L381-388).
- `CLS`, `CLS 2` (graphics-page clear during sprite capture), `VIEW PRINT 9 TO 24` / `VIEW PRINT 1 TO 25` (GorillaIntro).
- `Scl(n!)` (L1036-1049): CGA halving with quirk — **fractional inputs get `n! - 1` first in Mode 1** (so `Scl(2.9)` → 1, `Scl(6.9)` → 3); Mode 9 → `CINT(n!)` (banker's rounding!).
- `Radius = Mode MOD 7` in PlotShot (L905) — computed, **never used** (quirk).

## Sprite DATA (GET/PUT long-array format)

L125-141: `CGABanana:` 4 directions × 3 longs; `EGABanana:` 4 directions × 9 longs. Loaded via `RESTORE`/`READ` per mode in InitVars. First long = QBASIC GET header (width/height), rest = packed pixel data. Port must decode: header word layout + 2-bpp (CGA) / 4-bpp (EGA) planar packing — or regenerate sprites via DrawGorilla/capture equivalent. Gorilla sprites are NOT in DATA; captured at runtime by `GET` in DrawGorilla.

## Sound

All `PLAY` macro strings:

| Line | Context | Macro |
|---|---|---|
| L257 | DoExplosion | `MBO0L32EFGEFDC` (background) |
| L465 | ExplodeGorilla | `MBO0L16EFGEFDC` (background) |
| L628-643 | GorillaIntro dance (4 phrases) | `t120o1l16b9n0baan0bn0bn0baaan0b9n0baan0b`, `o2l16e-9n0e-d-d-n0e-n0e-n0e-d-d-d-n0e-9n0e-d-d-n0e-`, `o2l16g-9n0g-een0g-n0g-n0g-eeen0g-9n0g-een0g-`, `o2l16b9n0baan0g-n0g-n0g-eeen0o1b9n0baan0b` |
| L649/653 | GorillaIntro finale ×4 loop | `T160O0L32EFGEFDC` |
| L679 | Intro title screen | `MBT160O1L8CDEDCDL4ECC` (background, during SparklePause) |
| L921 | PlotShot throw | `MBo0L32A-L64CL16BL64A+` (background) |
| L1128/1131 | VictoryDance ×4 loop | `MFO0L32EFGEFDC` (foreground — blocks; sets the dance pace) |
- `BEEP` (GetNum# L566, invalid key).
- Macro features needed: `M B/F`, `O`, `L`, `T`, `N`, `A-G`, `+/-`, duration numbers, `P` (n0 rests). No `.`, `<`, `>`, `X` used — but parser should be reasonably complete.

## Input

- `LINE INPUT "...: "; Player$` ×2 (GetInputs L496, L504) — names truncated to 10 chars (`LEFT$`), defaults "Player 1"/"Player 2".
- `INPUT "Play to how many total points (Default = 3)"; game$` (L514) — `VAL(LEFT$(game$,2))`, loop until `NumGames > 0 AND LEN(game$) < 3 OR LEN(game$) = 0`; default 3.
- `INPUT "Gravity in Meters/Sec (Earth = 9.8)"; grav$` (L522) — loop until `gravity# > 0 OR LEN(grav$) = 0`; default 9.8.
- Pre-clear pattern: `LOCATE 12, 56: PRINT SPACE$(25);` / `LOCATE 14, 53: PRINT SPACE$(28);` before each INPUT retry.
- `GetNum#(Row, Col)` (L532-577): INKEY$ polling; accepts `0-9`, one `.`, Enter (rejects > 360 by clearing), Backspace; any other key → `BEEP`; echoes `Result$; CHR$(95); "    "` (underscore as fake cursor); clears keyboard buffer first (`WHILE INKEY$ <> "": WEND`).
- `INKEY$` wait loops: GorillaIntro choice `DO WHILE Char$ = "": Char$ = INKEY$: LOOP` (L591-593 — note the quirk: condition tests *before* first INKEY$, Char$ defaults ""), SparklePause exit, intro/game-over "Press any key".
- No STICK/STRIG, no mouse.

## Timing (everything routes through these)

- `CONST SPEEDCONST = 500` — user-tunable game speed (header comment L10-11).
- `CalcDelay!` (L228-236): busy-count `i! = i! + 1` for 0.5 s against `TIMER` → `MachSpeed` (×1.3 in CGA mode, L206).
- `Rest(t#)` (L1024-1031): busy-wait until `TIMER - s# > MachSpeed * t# / SPEEDCONST`.
- Callers of Rest: DoExplosion `.005`/ring; GorillaIntro `1, .3×4, .1×8`; PlotShot `.1` (throw pose), `.02` (per banana frame); VictoryDance `.2×8`.
- `SLEEP 1` after each game round (L876).
- `RANDOMIZE (TIMER)` per round (L854).
- Empty CPU-speed loops: DoExplosion `FOR i = 1 TO 100` (L267); ExplodeGorilla `FOR Count = 1 TO 200` (L479).
- CPU-paced animation: **SparklePause** (L1075-1110) — no delay at all, frame rate = whatever the CPU+blit gives; **PlotShot** banana loop paced by `Rest .02`; physics advanced by `t# = t# + .1` per frame regardless of wall time.
- Details and conversions: `TIMING_NOTES.md`.

## Low-level

- `DEF SEG = 0` + `PEEK(1047)` / `POKE 1047, ...` (L111-122): force NumLock ON (`&H417` keyboard flags, bit 5), restore on exit. **Port: no-op** (modern OS handles NumLock; document in QUIRKS.md).
- No INP/OUT, no CALL ABSOLUTE/INTERRUPT, no screen-memory pokes.

## Files

- None. No OPEN/GET#/PUT#/FIELD, no save files or high scores. (Scores are in-memory `TotalWins(1 TO 2)` only.)

## Error handling

- `ON ERROR GOTO ScreenModeError` (L146), `ON ERROR GOTO PaletteError` (L152), `ON ERROR GOTO 0` (L154).
- `ScreenModeError:` — if Mode = 1 → print requirement message + END; else Mode = 1, `RESUME`.
- `PaletteError:` — Mode = 1, `RESUME NEXT`.
- Port: model as capability probes with a config/flag; the "64K EGA" and CGA-fallback paths only matter if we offer `--mode` selection.

## Strings / formatting

- `Center(Row, Text$)`: `LOCATE Row, Col - (LEN(Text$)/2 + .5)` where `Col = MaxCol \ 2` — integer arithmetic on float expression; replicate exactly (floating LEN/2 + .5 then LOCATE truncates).
- `LTRIM$(STR$(TotalWins(1)))` in score line (L864) — STR$ leading space removed by LTRIM$.
- `SPACE$`, `LEFT$`, `UCASE$`, `VAL`, `INSTR`, `TAB(50)`, `MID$` (SparklePause), `CHR$(95)`, `CHR$(8)`, `CHR$(13)`.
- `PRINT Text$;` trailing-semicolon no-newline pattern everywhere.
- No PRINT USING.

## Control flow

- GOSUB/RETURN: only `GOSUB InitVars` (L117) → `RETURN` (L212).
- SELECT CASE: DrawBan, DrawGorilla arms, GetNum# keys, Slope (note **unreachable `CASE 4`** at L735, shadowed by `CASE 3 TO 5`).
- No ON...GOTO. DO/WHILE/FOR standard.

## Needs decision

All resolved by user answers above. Remaining estimates (documented, adjustable, low/medium confidence):

1. **MachSpeed/SPEEDCONST factor** — self-calibrating on real hardware; for the port, nominal Rest(t#) seconds with `--speed` multiplier (see TIMING_NOTES.md).
2. **SparklePause frame rate** — CPU-dependent in original; pick fixed ~10 fps for the 5-phase cycle.
3. **ExplodeGorilla/DoExplosion empty loops** — negligible (<10 ms); map to 0 or a few ms.
