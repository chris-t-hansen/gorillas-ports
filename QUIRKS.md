# QUIRKS.md — preserved bugs, omissions, and intentional deviations

_A living document. Each entry cites the source line and the decision._

## Preserved original quirks

1. **`Center()` integer-arithmetic quirk** (L242): `LOCATE Row, Col - (LEN(Text$)/2 + .5)` performs integer division on a float expression. The port replicates this exactly. *(game.py, not runtime)*

2. **`Scl()` fractional quirk** (L1036-1049): when `n!` is not an integer and Mode = 1 (CGA), `n!` is decremented by 1 before scaling. So `Scl(2.9)` → 1, `Scl(6.9)` → 3. The port replicates this exactly. *(game.py, not runtime)*

3. **`Radius = Mode MOD 7` in PlotShot** (L905): computed but **never used**. Dead code preserved in translation for traceability.

4. **Unreachable `CASE 4`** in Slope SELECT CASE (L735): shadowed by `CASE 3 TO 5`. Preserved as unreachable.

5. **Undeclared variables defaulting to 0**: `BACKGROUND` (L763, LINE color) and `MaxHeight` (L758) are never declared or assigned. In QBASIC DEFINT they default to 0. Port preserves this.

6. **Dead DECLAREs**: `EndGame` (L27) and `Getn#` (L47) are declared but never defined or called. Dropped from port.

## Intentional deviations from original

7. **NumLock PEEK/POKE** (L111-122, `&H417`): the original forces NumLock ON via BIOS memory. The port is a **no-op** — modern OSes manage NumLock. Behavior: NumLock state is unchanged.

8. **RND sequences**: exact QBASIC LCG sequences are NOT reproduced (per user decision). Python's `random` module is used instead. Seeded from `time.time()` like `RANDOMIZE TIMER`.

9. **OS key-repeat**: the port uses the operating system's key-repeat rate rather than emulating the DOS BIOS typematic (~2 char/s after 500ms delay, then ~10/s). Acceptable for Gorillas which doesn't depend on held-key timing.

10. **EGA SCREEN 0 geometry**: the port uses 640×350 with 8×14 font for SCREEN 0 (matching SCREEN 9 for seamless mode switches). Real VGA hardware would use 720×400 with 9×16 font. Documented choice per user preference for consistency.

11. **`files.py` not needed**: Gorillas has no file I/O (no OPEN, GET#, PUT#, no save files). The `files.py` module from the SKILL layout is omitted.

12. **`PALETTE` color values**: the EGA 6-bit decode formula is correct and verified against all standard anchors. Some earlier reference sources had incorrect values for EGA 44 and EGA 54; the port uses the mathematically correct values: 44=(255,0,85) and 54=(255,255,0).
