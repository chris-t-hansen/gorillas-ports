---
name: qbasic-to-python-retro
description: Convert a QBASIC / QuickBASIC (.BAS) program from the DOS era into a modern, standalone Python program that looks, sounds, and behaves like the original did on a real early-90s PC, without needing DOSBox or any emulator. Use this skill whenever the user mentions QBASIC, QuickBASIC, QB45, .BAS files, DOS BASIC games, porting or converting old BASIC code to Python, or wants retro text-mode or VGA/CGA output reproduced faithfully. Also use it for fixing speed problems caused by CPU-speed-dependent delay loops in old code, even if the user never says "QBASIC" explicitly.
---

# QBASIC to Python: faithful retro conversion

## Goal

Produce a Python program that:

1. Runs natively on modern Windows, macOS, and Linux. No emulator, no DOSBox, no VM.
2. Looks **pixel- and character-identical** to the original: same text layout, colors, fonts, graphics, screen modes.
3. Behaves identically, including quirks and bugs, except for timing.
4. Runs at the speed the author **intended**, not the speed of a 286/386 or the blazing speed of a modern CPU. Anything that depended on processor clock speed becomes real-time seconds.

This is a **preservation port**, not a modernization. Do not "improve" the game.

## Ground rules

- **Do not change behavior, text, layout, spelling, or color choices**, even if they look wrong. Preserve original bugs unless they crash or are physically impossible on modern systems. List every preserved quirk in `QUIRKS.md`.
- **Do not refactor for style** if doing so risks changing output. Idiomatic Python is welcome only where it is provably equivalent.
- Keep a traceable link to the source: each translated block gets a comment like `# BAS line 142-158` (or the original label/SUB name).
- You may create a virtual environment and `pip install` libraries when the standard library cannot do the job. Pin versions in `requirements.txt`. Prefer the standard library whenever it can truly replicate the behavior.
- If something is ambiguous (unknown intended delay, missing DATA, an unclear screen mode), **ask the user** rather than guessing silently. Batch your questions into one message.
- Never run the original .BAS through an emulator as part of the final product. (If the user supplies reference screenshots or recordings, use them for comparison only.)

## Workflow

### Step 1: Inventory the source

Read the entire .BAS file(s) before writing any Python. Produce `INVENTORY.md` containing:

- Screen mode(s) used (`SCREEN 0, 1, 2, 7, 8, 9, 12, 13`) and any `WIDTH` changes
- Every `COLOR`, `PALETTE`, `PALETTE USING`, `OUT &H3C8/&H3C9` usage
- Graphics statements used: `PSET, PRESET, LINE (incl. B / BF / styles), CIRCLE, PAINT, DRAW, GET, PUT (incl. XOR/PSET/AND/OR/PRESET), VIEW, WINDOW, POINT`
- Sound statements: `BEEP, SOUND, PLAY`
- Input: `INKEY$, INPUT, LINE INPUT, INPUT$, STICK/STRIG, mouse via CALL INTERRUPT`
- Timing: every `TIMER`, `SLEEP`, empty `FOR...NEXT` delay loop, `PLAY` tempo, `SOUND` durations, and any busy-wait
- Low-level: `PEEK, POKE, DEF SEG, INP, OUT, CALL ABSOLUTE, CALL INTERRUPT`
- Files: `OPEN, GET/PUT (random), FIELD, LSET/RSET, MKI$/CVI$` and similar, `DATA/READ/RESTORE`
- Control flow: `GOTO/GOSUB` density, `ON ... GOTO/GOSUB`, `ON ERROR`, `RESUME`
- `$INCLUDE`, `DECLARE`, `COMMON`, `CHAIN`, `RUN`, multiple modules
- Variable types and suffixes (`%`, `&`, `!`, `#`, `$`), `DEFINT/DEFSNG/DEFSTR`, `TYPE` records, `DIM` bounds, `OPTION BASE`

Anything that cannot be mapped cleanly goes in a "Needs decision" section and is raised with the user.

### Step 2: Build a small runtime layer first

Do not scatter hardware emulation across game logic. Create a `qb_runtime/` package that provides QBASIC semantics, then write the game on top of it so the translated game code reads almost line for line like the original.

Suggested layout:

```
project/
  game.py                 # translated program, close to line for line
  qb_runtime/
    __init__.py
    screen.py             # modes, text grid, graphics surface, palette, scaling
    text.py               # PRINT, LOCATE, COLOR, CLS, cursor, scrolling, zones
    graphics.py           # PSET, LINE, CIRCLE, PAINT, DRAW, GET, PUT
    keyboard.py           # INKEY$, INPUT, LINE INPUT, scan codes
    sound.py              # SOUND, BEEP, PLAY (music macro language)
    timing.py             # all delay/time handling (see Step 4)
    rng.py                # RND / RANDOMIZE
    files.py              # sequential and random file I/O
    format.py             # PRINT USING, STR$, number formatting
  assets/
    fonts/                # bitmap font data + license file
  TIMING_NOTES.md
  QUIRKS.md
  INVENTORY.md
  requirements.txt
  README.md
  tests/
```

### Step 3: Make it look exactly the same

#### Rendering approach (default)

Use **pygame** (install via pip in a venv) to open a window and draw to an off-screen surface at the **native resolution of the original screen mode**, then scale it up by an **integer factor** with **nearest-neighbor** scaling (no smoothing, no blur). Letterbox rather than stretch non-uniformly.

Native geometry reference:

| Mode | Resolution | Colors | Notes |
|---|---|---|---|
| SCREEN 0 | 80x25 text (720x400 on VGA, 9x16 cells; 640x350 EGA 8x14; 640x200 CGA 8x8) | 16 fg / 8 bg (+ blink) | Match what the author's hardware most likely showed; ask if unsure |
| SCREEN 1 | 320x200 | 4 (CGA palette) | |
| SCREEN 2 | 640x200 | 2 | |
| SCREEN 7 | 320x200 | 16 | |
| SCREEN 8 | 640x200 | 16 | |
| SCREEN 9 | 640x350 | 16 of 64 | |
| SCREEN 12 | 640x480 | 16 of 262144 | |
| SCREEN 13 | 320x200 | 256 | |

Pixel aspect ratio: 320x200 and 640x200 modes were displayed on 4:3 monitors, so pixels were not square (roughly 1:1.2). Present the 320x200 surface at 4:3 (for example scale to 960x720, or 1280x960) unless the user says otherwise. Document the choice.

#### Text mode details that matter

- **Font**: use a real IBM VGA bitmap font (8x16 or 9x16 for SCREEN 0 on VGA; 8x8 for CGA modes). Render glyphs from bitmap data, not a modern TTF at some size. A freely licensed option is the Px437 IBM VGA fonts from "The Ultimate Oldschool PC Font Pack" (check and include its license in `assets/fonts/`). If the agent cannot obtain a font, ask the user to supply one, and do not silently substitute a modern font.
- **Character set**: Code Page 437. Use Python's `cp437` codec. Box-drawing characters, smileys (chr 1-31 render as glyphs, not control codes), and block elements must display as in DOS. `PRINT CHR$(7)` is a beep; many other low codes print glyphs.
- **Color**: use the exact 16-color VGA/CGA text palette (not "close enough"): 
  `#000000 #0000AA #00AA00 #00AAAA #AA0000 #AA00AA #AA5500 #AAAAAA #555555 #5555FF #55FF55 #55FFFF #FF5555 #FF55FF #FFFF55 #FFFFFF` 
  Note color 6 (brown) is `#AA5500`, not dark yellow. For SCREEN 1 use the CGA palettes 0 and 1 as defined in the QBASIC docs.
- **Blink**: `COLOR fg+16` blinks in SCREEN 0. Implement blinking at about 1.875 Hz (VGA blink rate; about 266 ms on, 266 ms off).
- **Cursor**: the underscore-style hardware cursor, blinking, shown during `INPUT` and when `LOCATE ,,1`. `LOCATE row, col, cursor, start, stop` must respect cursor shape.
- **Scrolling**: printing past row 25 scrolls the screen. A trailing `;` on `PRINT` suppresses the newline. `PRINT` on the last row without `;` scrolls. Writing to row 25 col 80 behaves specially. Match these.
- **PRINT zones**: a comma advances to the next 14-column zone. Numbers print with a leading space for positives and a trailing space. `PRINT` of a single-precision number follows QBASIC's exact formatting rules (e.g. `1E+10`, `.5`, `3.14159`). Implement a dedicated `qb_str(x)` and test it against many values.
- **`WIDTH 40`**, `WIDTH 80`, `WIDTH ,43/50` change the grid; support them if used.
- **`VIEW PRINT`**, `CLS 0/1/2`: support if used.

#### Graphics details

- Implement drawing primitives to match QBASIC's output **pixel for pixel**: Bresenham-style `LINE`, QBASIC's `CIRCLE` (including aspect ratio and arc start/end angles, in radians), `PAINT` with border color and tiling patterns, `DRAW` macro language (`U D L R E F G H M B N A TA C S P`), `GET/PUT` array formats and action verbs.
- `CIRCLE` and `PAINT` have subtle behaviors; do not substitute pygame's built-in circle without checking it matches the QBASIC shape. Write your own rasterizers.
- Palette changes (`PALETTE n, c`) must update already-drawn pixels immediately, as on real VGA. Therefore keep an **indexed-color framebuffer** (pixel = palette index) and apply the palette at present time. Do not store RGB at draw time.
- `SCREEN` mode switches clear the screen and reset the palette, as in the original.

#### What not to do

- No anti-aliasing, smoothing, CRT filters, or scanline effects unless the user asks.
- No modern window chrome tweaks that change the displayed content area. A plain resizable or fixed window is fine.

### Step 4: Fix all processor-speed dependence (critical)

On a 286/386 these were tuned by feel to look right. On a modern CPU they run effectively instantly. Convert **every** such construct to real wall-clock time.

Create `qb_runtime/timing.py` as the **single source of truth** for time. All timing constants live in one table at the top of the file (or in `timing_config.py`), each with a comment citing the source line and the reasoning. The user must be able to tweak them in one place.

Rules:

1. **Empty delay loops** (`FOR i = 1 TO 5000: NEXT i`, with or without a trivial body):
   - Replace with `qb.delay(seconds)`.
   - Estimate the intended seconds from the loop count. As a rough guide, a QBASIC empty `FOR/NEXT` ran on the order of ~25,000-50,000 iterations/second on a 286 and ~100,000-200,000/second on a 386/486 *in the QBASIC interpreter*. Compiled QuickBASIC was several times faster. Use that as a starting estimate only, and state your assumption.
   - Prefer anchoring to the **author's intent** visible in context (a "Get Ready!" message that should linger about 2 seconds; an animation frame that should hold ~0.1 s). Where the code gives clues (comments, nearby `SLEEP`, `TIMER` use), use them.
   - Record each conversion in `TIMING_NOTES.md` as: source line | original loop count | assumed original speed | resulting seconds | confidence (high/medium/low).
   - For any low-confidence delay, **ask the user** what felt right when they played it.
2. **`TIMER`-based waits** (`start = TIMER: DO: LOOP WHILE TIMER < start + 1`): `TIMER` already counts real seconds since midnight (resolution ~1/18.2 s). Keep the semantics, but implement via `time.monotonic()` and sleep/yield instead of burning CPU. Handle the midnight rollover if the original did.
3. **`SLEEP n`**: n real seconds; `SLEEP` with no argument waits for a keypress. Any key press ends a timed `SLEEP` early.
4. **`SOUND freq, duration`**: duration is in **clock ticks at 18.2 ticks per second**, not seconds. So `SOUND 440, 18.2` is one second. Frequency range 37-32767 Hz.
5. **`PLAY`**: parse the full music macro language (`O L T P N A-G # + - . < > MN ML MS MF MB`, `X` variable substitution). `T` is quarter notes per minute (32-255, default 120). Default `L4`, default `O4`, default `MN` (7/8 of the note duration sounding). Play synchronously (`MF`, default) or in the background (`MB`) as in the original.
6. **Game loops that run "as fast as possible"** (move a sprite each pass through a `DO...LOOP` with no delay): on the original, speed was set by CPU and the work done each pass. Convert to a **fixed timestep**, with the step rate chosen to reproduce the intended feel. Common targets: 18.2 Hz (the BIOS tick), 10, 15, 30 Hz. Pick one, document it in `TIMING_NOTES.md`, and make it a named constant. If the author left no clue, ask the user how fast it felt, or offer two or three candidate speeds to try.
7. **Keyboard polling**: `INKEY$` returns immediately (empty string if no key). Inside tight loops this is fine, but throttle the loop with the fixed timestep so input checking does not eat a whole CPU core.
8. **Typematic / key repeat**: DOS BIOS repeat was about 2 characters per second initially after a ~500 ms delay, then ~10 per second. Ask the user whether they want this emulated or the OS's key repeat to be used, if the game depends on held keys.
9. **Never use `time.sleep()` in a way that freezes the window.** Pump the event queue during every wait so the window stays responsive (and the close button works).
10. **Frame presentation**: only redraw the window when something changed or on a ~60 Hz timer, independently of game timing. Game-logic timing and screen refresh rate are separate concerns.

### Step 5: Translate the language semantics faithfully

Common traps (check each against the source):

- **Arrays** are 0-based or 1-based depending on `DIM x(1 TO n)` / `OPTION BASE`. Preserve exact indices. Use a small wrapper class if bounds differ from 0.
- **Integer types**: `INTEGER` is 16-bit signed (-32768 to 32767) and overflows with an error in QBASIC (Overflow, error 6). `LONG` is 32-bit. Default numeric type is single-precision float (about 7 digits), so emulate it with `numpy.float32` or `struct`-based rounding when the output depends on it (e.g. printed values, loop accumulators). Do not use Python's 64-bit floats if it changes visible numbers.
- **Integer division and rounding**: `\` is integer division truncating toward zero; `MOD` truncates operands to integers; `INT()` floors, `FIX()` truncates; `CINT()` rounds half to even ("banker's rounding"). Python's `//`, `%`, and `round()` differ in places. Write helper functions.
- **Strings**: 1-based `MID$`, `LEFT$`, `RIGHT$`, `INSTR`; `MID$` as a statement; fixed-length strings (`DIM s AS STRING * 10`) pad with spaces; `LSET/RSET`. `STR$(n)` adds a leading space for non-negative numbers.
- **`RND`**: QBASIC's generator is deterministic given a seed. `RANDOMIZE TIMER` is fine to translate as seeding from time. If the program uses `RANDOMIZE <fixed seed>` or `RND(-1)` with expectations of identical sequences, reproduce QBASIC's algorithm exactly (it is a documented linear congruential generator; implement it in `rng.py` and test known sequences). Otherwise, ask the user whether exact sequences matter.
- **`PRINT USING`**: implement the format-string rules (`#`, `.`, `,`, `$$`, `**`, `^^^^`, `_`, `&`, `!`, `\ \`).
- **`GOTO`/`GOSUB` spaghetti**: if the program is heavily label-driven, translate to a state machine or a `while True` dispatcher using a `pc`/label variable, with each label becoming a function or a case. Preserve semantics of `GOSUB/RETURN` with an explicit return stack, and of `ON x GOTO`. Do not restructure into "cleaner" logic if it risks changing behavior.
- **`ON ERROR GOTO` / `RESUME`**: map to try/except with equivalent QBASIC error codes (e.g. 53 File not found, 6 Overflow, 11 Division by zero). Keep user-visible error messages identical.
- **`INPUT`**: prints `? ` after the prompt (a `;` after the prompt string keeps it, a `,` removes it), handles backspace, rejects bad numeric input with `Redo from start`. Reproduce those messages.
- **`INKEY$`**: extended keys return a 2-character string starting with `CHR$(0)` followed by the scan code (arrows: 72 up, 80 down, 75 left, 77 right; function keys 59-68). Build a table mapping pygame keys to the original codes. Handle Enter = `CHR$(13)`, Esc = `CHR$(27)`, Backspace = `CHR$(8)`, Tab = `CHR$(9)`.
- **`PEEK`/`POKE`/`DEF SEG`/`INP`/`OUT`**:
  - Common cases to emulate: keyboard shift flags at `&H417` (via `DEF SEG = 0`), screen memory at `&HB800` (text) or `&HA000` (graphics), the BIOS timer tick at `&H46C`, VGA palette ports `&H3C7-&H3C9`, and the PC speaker via ports `&H42/&H43/&H61`.
  - Provide a **virtual memory map** in the runtime so these keep working (e.g. poking `&HB800:offset` updates the text grid; reading `&H46C` returns the tick counter derived from real time at 18.2 Hz).
  - Anything else: stop and ask the user.
- **`CHAIN`/`RUN`/`SHELL`/`CALL ABSOLUTE`**: do not ship these as-is. Replace with Python module calls or ask.
- **Files**: preserve on-disk formats (record lengths, `MKI$`/`CVI$` binary layouts, `.DAT` files) so original save files and high-score tables still load. Handle DOS-style paths and 8.3 file names by mapping them to the project directory.
- **Case insensitivity** and **`DEFINT A-Z`**-style implicit typing: variable names `a`, `A`, `a%`, `a$` are different variables only by suffix, not by case. Normalize accordingly.

### Step 6: Sound

- Use `pygame.mixer` (or `sounddevice`, if pygame audio proves unreliable) with **numpy**-generated **square waves** to mimic the PC speaker: 50% duty cycle, 44.1 kHz (or 22.05 kHz) mono, 16-bit, no filtering and no reverb. The PC speaker was harsh; keep it harsh.
- Short envelope clicks are authentic. Do not add fades unless the user requests it to avoid pops, in which case use a ~1 ms ramp and say so in `README.md`.
- `BEEP` is about an 800 Hz square wave for about 0.25 s (check if the original used another via `SOUND`). `PLAY` and `SOUND` block until finished unless `PLAY "MB"` was used.
- Provide a `--mute` flag.

### Step 7: Verification

Before calling the work done:

1. **Run it.** Launch the program, drive it through every screen, and confirm no crashes.
2. **Text screens**: write a test that dumps the 80x25 character + attribute grid after key moments and compare against expected grids derived from the source (or from user-provided screenshots). Add golden-file tests under `tests/`.
3. **Graphics**: save framebuffer PNGs for key screens at native resolution. Compare by eye against any reference screenshots from the user. Ask the user to send photos or screenshots of the original if available.
4. **Formatting**: unit-test `qb_str`, `PRINT USING`, `CINT`, `MOD`, `\`, `INT`, `FIX`, string functions with many edge cases (negatives, .5 rounding, large and small magnitudes).
5. **Timing**: instrument each converted delay and verify it matches the seconds in `TIMING_NOTES.md` within ~5%. Confirm no loop pins a CPU core at 100% while idle.
6. **Cross-platform sanity**: the program should start with `python game.py` after `pip install -r requirements.txt`. No platform-specific paths. Test or at least statically review for Windows path handling.
7. **Quirks audit**: re-read the source one last time looking for behavior you may have "fixed" by accident.

### Step 8: Deliverables

- `game.py` (and any helper modules) plus `qb_runtime/`
- `requirements.txt` with pinned versions
- `README.md`: how to create the venv, install, run; controls; command-line flags (`--scale N`, `--mute`, `--fullscreen`, `--speed X` multiplier for timing tweaks)
- `TIMING_NOTES.md`: every delay/speed conversion, assumptions, and confidence
- `QUIRKS.md`: preserved bugs and any intentional deviations (should be nearly empty)
- `INVENTORY.md`: from Step 1
- `tests/`
- Optional if the user asks: a PyInstaller recipe to produce a single-file executable per OS

Standard setup instructions to include in the README:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python game.py
```

## Questions to ask the user up front (if not already answered)

Ask these in a single message before starting:

1. Please share the .BAS file(s), plus any data files, save files, or included modules.
2. Do you have screenshots or photos of the original running? What monitor/graphics card era did you play it on (CGA, EGA, VGA)?
3. Were you running it inside the QBASIC IDE (interpreted) or as a compiled .EXE? This affects speed estimates a lot.
4. What CPU speed did you play it on, and did it feel too fast, too slow, or right?
5. Should the window be fixed-size, resizable, or fullscreen by default? Preferred scale factor?
6. Do you want the original 4:3 pixel aspect ratio for 320x200 modes (recommended), or square pixels?
7. Is exact `RND` sequence reproduction important (for example, seeded levels)?

## Communication style while working

- Report progress by Step number.
- Surface decisions that affect look or feel as soon as you hit them; do not bury them in the final summary.
- When you estimate a timing, say it is an estimate and say how to change it.
- Keep the final summary short: what runs, what to try, what you need the user to judge by eye.
