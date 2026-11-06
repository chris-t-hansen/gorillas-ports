# TIMING_NOTES.md — delay and speed conversions

_Every timing construct from the original source, its conversion, and confidence level._

## Design principle

The original's `Rest(t#)` was designed so that **`Rest(t#)` ≈ t# seconds** on the author's reference machine (where `MachSpeed ≈ SPEEDCONST = 500`). The port maps `Rest(t#)` → wall-clock wait of `t# / speed_multiplier` seconds, controlled by `--speed` flag.

## Timing table

| Source | Line | Original construct | Converted to (seconds) | Confidence | Notes |
|---|---|---|---|---|---|
| CalcDelay! | L228-236 | Count iterations for 0.5s vs TIMER | Not used directly; sets MachSpeed = 500 (nominal) | medium | Self-calibrating on real hardware; port uses fixed SPEEDCONST |
| MachSpeed × 1.3 | L206 | CGA speed boost | Not used; CGA mode has same timing in port | low | Could be added if CGA feels too slow |
| Rest .005 | L266 | DoExplosion per-ring | 0.005 / speed | medium | Very short delay; barely perceptible |
| FOR i=1 TO 100 | L267 | DoExplosion empty loop | ~0 (negligible, < 5ms) | high | Loop body is empty; mapped to 0 |
| Rest 1 | L630 | GorillaIntro | 1.0 / speed | high | "Get ready" pause |
| Rest .3 × 4 | L636-643 | GorillaIntro dance phrases | 0.3 / speed each | medium | Between dance moves |
| Rest .1 × 8 | L644-648 | GorillaIntro finale | 0.1 / speed each | medium | Quick pauses |
| Rest .1 | L927 | PlotShot throw pose | 0.1 / speed | high | Player sees throw angle |
| Rest .02 | L956 | PlotShot per banana frame | 0.02 / speed | medium | Banana animation speed |
| Rest .2 × 8 | L1126 | VictoryDance | 0.2 / speed each | high | Dance step timing |
| SLEEP 1 | L876 | End of round | 1.0 real seconds | high | Any key ends early |
| FOR Count=1 TO 200 | L479 | ExplodeGorilla empty loop | ~0 (negligible) | high | Mapped to 0 |

## CPU-paced animations

| Animation | Source | Original behavior | Port behavior | Notes |
|---|---|---|---|---|
| SparklePause | L1075-1110 | CPU-dependent, no delay | ~10 fps fixed frame rate | 5-phase sparkle cycle; adjustable |
| PlotShot banana loop | L915-980 | `t# += .1` per frame, paced by `Rest .02` | 0.02s / speed per frame | Physics step is fixed at 0.1 regardless of wall time |

## PLAY tempo

| Macro | Line | Tempo | Duration estimate | Notes |
|---|---|---|---|---|
| DoExplosion | L257 | MB, default T120 | ~0.5s background | Doesn't block |
| ExplodeGorilla | L465 | MB, default T120 | ~0.5s background | Doesn't block |
| GorillaIntro dance | L628-643 | T120, L16 | ~4s total (4 phrases) | Background |
| GorillaIntro finale | L649/653 | T160, L32 | ~0.5s per loop × 4 | Foreground |
| Intro title | L679 | MB, T160, L8 | ~2s background | During SparklePause |
| PlotShot throw | L921 | MB, L32/L64/L16 | ~0.3s background | Quick throw sound |
| VictoryDance | L1128/1131 | MF, L32 | ~0.5s per loop × 4 | **Foreground** — sets dance pace |

## TIMER

- QBASIC `TIMER` = seconds since local midnight, ~55ms resolution (1/18.2s BIOS tick).
- Port: `time.monotonic()`-based, higher resolution, midnight rollover preserved.
- Used by CalcDelay! (not used in port) and RANDOMIZE TIMER (port uses time.time()).

## `--speed` flag

Multiplies all `Rest()` durations. Default = 1.0.
- `--speed 0.5` = half speed (delays are 2× longer)
- `--speed 2.0` = double speed (delays are 0.5× as long)

Does NOT affect `SLEEP` (always real seconds) or `PLAY` tempo.

## Step 4 verification (game.py wiring)

The `--speed` flag is wired end-to-end through:
1. CLI argument `--speed X` → `timing.set_speed(X)` in `game.py main()`
2. `timing.rest(t)` divides by speed multiplier before wall-clock wait
3. `timing._pump_wait()` pumps pygame events + presents during all waits
4. `timing.sleep()` pumps events + checks for key interrupt

All `Rest()` calls in game.py route through `timing.rest()`:
- `rest(0.1)` — throw pose (PlotShot L927)
- `rest(0.02)` — banana animation frame (PlotShot L956)
- `rest(0.005)` — explosion ring (DoExplosion L266)
- `rest(1)` / `rest(0.3)` / `rest(0.1)` — GorillaIntro dance
- `rest(0.2)` — VictoryDance

`SLEEP 1` → `timing.sleep(1)` (real seconds, any key ends early).

SparklePause uses `timing._pump_wait(0.05)` for ~20 fps sparkle cycle.
