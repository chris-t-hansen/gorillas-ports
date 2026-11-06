"""qb_runtime.format — QBASIC string and number formatting.

Implements STR$-equivalent (qb_str), VAL, and the 1-based string functions:
LEFT$, RIGHT$, MID$, INSTR, SPACE$, STRING$, UCASE$, LCASE$, LTRIM$, RTRIM$.

All functions are pure and side-effect-free.
"""

import math
import re


# ---------------------------------------------------------------------------
# Number → string (STR$ equivalent)
# ---------------------------------------------------------------------------


def qb_str(x) -> str:
    """Format a number as QBASIC's STR$ would.

    Rules:
    - Positive values (including 0) get a leading space.
    - Negative values get a leading '-'.
    - Integers are printed without a decimal point.
    - Doubles use fixed-point when practical, exponential otherwise.
    - Exponential form: d.ddddddE+dd or d.ddddddE-dd (up to ~15 significant digits).
    - Values like 0.5 print as '.5' only in some QBASIC contexts; STR$ prints '0.5'.
      (PRINT with a bare expression prints '.5' — that's handled in text.py.)
    """
    if isinstance(x, int):
        s = str(x)
        return (" " + s) if x >= 0 else s

    # Float path — determine if we should use exponential notation.
    if x == 0.0:
        return " 0" if not math.copysign(1.0, x) == -1.0 else " 0"

    sign = "" if x > 0 else "-"
    ax = abs(x)

    # QBASIC STR$ uses exponential for |x| >= 1e15 or |x| < 0.1 (and != 0).
    if ax >= 1e15 or (ax < 0.1 and ax != 0.0):
        # Exponential: up to 15 significant digits, strip trailing zeros.
        # Format: d.ddddddddddddddE+dd  (sign in mantissa handled separately)
        exp = math.floor(math.log10(ax))
        mantissa = ax / (10.0 ** exp)
        # Format mantissa with up to 15 digits after decimal.
        m_str = f"{mantissa:.15f}".rstrip("0").rstrip(".")
        exp_sign = "+" if exp >= 0 else "-"
        return f" {sign}{m_str}E{exp_sign}{abs(exp):02d}" if x >= 0 else f"{sign}{m_str}E{exp_sign}{abs(exp):02d}"
    else:
        # Fixed-point: up to 15 significant digits total.
        # Determine how many digits are before the decimal point.
        if ax >= 1.0:
            int_digits = math.floor(math.log10(ax)) + 1
        else:
            int_digits = 0
        frac_digits = max(0, 15 - int_digits)
        s = f"{ax:.{frac_digits}f}".rstrip("0").rstrip(".")
        return (" " + sign + s) if x >= 0 else (sign + s)


def qb_str_single(x: float) -> str:
    """Format a single-precision float as QBASIC's STR$ would.

    Single-precision gives ~7 significant digits.
    """
    import struct

    # Round to float32 first.
    x = struct.unpack("f", struct.pack("f", float(x)))[0]

    if x == 0.0:
        return " 0"

    sign = "" if x > 0 else "-"
    ax = abs(x)

    if ax >= 1e7 or (ax < 0.1 and ax != 0.0):
        exp = math.floor(math.log10(ax))
        mantissa = ax / (10.0 ** exp)
        m_str = f"{mantissa:.7f}".rstrip("0").rstrip(".")
        exp_sign = "+" if exp >= 0 else "-"
        return f" {sign}{m_str}E{exp_sign}{abs(exp):02d}" if x >= 0 else f"{sign}{m_str}E{exp_sign}{abs(exp):02d}"
    else:
        if ax >= 1.0:
            int_digits = math.floor(math.log10(ax)) + 1
        else:
            int_digits = 0
        frac_digits = max(0, 7 - int_digits)
        s = f"{ax:.{frac_digits}f}".rstrip("0").rstrip(".")
        return (" " + sign + s) if x >= 0 else (sign + s)


# ---------------------------------------------------------------------------
# VAL — parse leading numeric portion of a string
# ---------------------------------------------------------------------------

# Regex: optional whitespace, optional sign, digits with optional decimal,
# optional exponent. QBASIC VAL also accepts &H, &O prefixes (hex/octal)
# and type suffixes (! # % &) which are consumed but ignored.
_VAL_RE = re.compile(
    r"^\s*"
    r"([+-]?)"
    r"(?:"
    r"&[Hh]([0-9A-Fa-f]+)"  # hex
    r"|&[Oo]([0-7]+)"  # octal
    r"|(\d+(?:\.\d*)?|\.\d+)(?:[EeDd]([+-]?\d+))?"  # decimal + optional exp
    r")"
)


def val(s: str) -> float:
    """QBASIC VAL() — parse leading numeric portion of a string.

    Returns 0 if no numeric prefix is found.
    Handles &H (hex), &O (octal), scientific notation (E/D exponent).
    Ignores trailing type suffixes (! # % &).
    """
    s = str(s)
    m = _VAL_RE.match(s)
    if not m:
        return 0.0
    sign_str, hex_str, oct_str, dec_str, exp_str = m.groups()
    sign = -1 if sign_str == "-" else 1

    if hex_str:
        return float(sign * int(hex_str, 16))
    if oct_str:
        return float(sign * int(oct_str, 8))
    if dec_str:
        base = float(dec_str)
        if exp_str:
            base *= 10.0 ** int(exp_str)
        return sign * base
    return 0.0


# ---------------------------------------------------------------------------
# 1-based string functions
# ---------------------------------------------------------------------------


def left(s: str, n: int) -> str:
    """LEFT$(s, n) — first n characters. n <= 0 → empty string."""
    if n <= 0:
        return ""
    return s[:n]


def right(s: str, n: int) -> str:
    """RIGHT$(s, n) — last n characters. n <= 0 → empty string."""
    if n <= 0:
        return ""
    if n >= len(s):
        return s
    return s[-n:]


def mid(s: str, start: int, length: int = -1) -> str:
    """MID$(s, start[, length]) — substring, 1-based.

    start < 1 → error 5 in QBASIC; we clamp to 1 for safety.
    If length omitted or -1, return from start to end.
    """
    if start < 1:
        start = 1
    idx = start - 1  # convert to 0-based
    if length < 0:
        return s[idx:]
    return s[idx : idx + length]


def instr(start: int, s: str, sub: str) -> int:
    """INSTR([start,] s, sub) — 1-based position of sub in s.

    Returns 0 if not found. start < 1 → error 5 in QBASIC; we clamp to 1.
    """
    if start < 1:
        start = 1
    idx = s.find(sub, start - 1)
    return (idx + 1) if idx >= 0 else 0


# ---------------------------------------------------------------------------
# String generation
# ---------------------------------------------------------------------------


def space(n: int) -> str:
    """SPACE$(n) — string of n spaces. n <= 0 → empty."""
    return " " * max(0, n)


def string_(n: int, ch) -> str:
    """STRING$(n, ch) — string of n copies of ch.

    ch can be a single character or an integer (ASCII code).
    n <= 0 → empty string.
    """
    if n <= 0:
        return ""
    if isinstance(ch, int):
        c = chr(ch & 0xFF)
    else:
        c = str(ch)[0] if ch else " "
    return c * n


# ---------------------------------------------------------------------------
# Case conversion
# ---------------------------------------------------------------------------


def ucase(s: str) -> str:
    """UCASE$(s)."""
    return s.upper()


def lcase(s: str) -> str:
    """LCASE$(s)."""
    return s.lower()


# ---------------------------------------------------------------------------
# Trimming
# ---------------------------------------------------------------------------


def ltrim(s: str) -> str:
    """LTRIM$(s) — strip leading spaces only."""
    return s.lstrip(" ")


def rtrim(s: str) -> str:
    """RTRIM$(s) — strip trailing spaces only."""
    return s.rstrip(" ")


# ---------------------------------------------------------------------------
# CHR$, ASC (thin wrappers for clarity)
# ---------------------------------------------------------------------------


def chr_(n: int) -> str:
    """CHR$(n) — character from code point."""
    return chr(n & 0xFF)


def asc(s: str) -> int:
    """ASC(s) — code point of first character. Empty string → error 5; we return 0."""
    if not s:
        return 0
    return ord(s[0])
