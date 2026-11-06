"""qb_runtime.qbmath — QBASIC numeric semantics.

Implements CINT (banker's rounding), INT (floor), FIX (truncate toward zero),
integer division (\\), MOD, 16-bit signed integer overflow, and single-precision
(float32) wrapping.

All functions are pure and side-effect-free.
"""

import struct

# ---------------------------------------------------------------------------
# 16-bit signed integer range (DEFINT A-Z default type)
# ---------------------------------------------------------------------------
_INT16_MIN = -32768
_INT16_MAX = 32767


class QBOverflowError(OverflowError):
    """Raised on QBASIC error 6 (Overflow)."""

    def __init__(self, msg: str = "Overflow"):
        super().__init__(msg)
        self.qb_error = 6


class QBDivisionByZeroError(ZeroDivisionError):
    """Raised on QBASIC error 11 (Division by zero)."""

    def __init__(self, msg: str = "Division by zero"):
        super().__init__(msg)
        self.qb_error = 11


# ---------------------------------------------------------------------------
# Rounding / truncation
# ---------------------------------------------------------------------------


def cint(x: float) -> int:
    """QBASIC CINT() — round to nearest integer, half-to-even (banker's rounding).

    CINT(0.5) = 0, CINT(1.5) = 2, CINT(2.5) = 2, CINT(-0.5) = 0, CINT(-1.5) = -2.
    Returns a Python int; does NOT overflow-check (call int16() if needed).
    """
    # Python's built-in round() uses banker's rounding, matching QBASIC exactly.
    return int(round(x))


def int_(x: float) -> int:
    """QBASIC INT() — floor toward negative infinity.

    INT(3.7) = 3, INT(-3.7) = -4.
    """
    import math

    return math.floor(x)


def fix_(x: float) -> int:
    """QBASIC FIX() — truncate toward zero.

    FIX(3.7) = 3, FIX(-3.7) = -3.
    """
    return int(x)  # Python int() truncates toward zero, matching FIX.


# ---------------------------------------------------------------------------
# Integer division and MOD
# ---------------------------------------------------------------------------


def _truncate_to_int(x) -> int:
    """Truncate a number toward zero (QBASIC's implicit conversion for \\ and MOD)."""
    return int(x)


def idiv(a, b) -> int:
    """QBASIC integer division (a \\\\ b).

    Both operands are truncated toward zero before division.
    The result is truncated toward zero (not floored).
    Raises QBDivisionByZeroError if b == 0.
    """
    a = _truncate_to_int(a)
    b = _truncate_to_int(b)
    if b == 0:
        raise QBDivisionByZeroError()
    # Python's int division truncates toward negative infinity;
    # QBASIC truncates toward zero. Use abs + sign correction.
    sign = -1 if (a < 0) != (b < 0) else 1
    return sign * (abs(a) // abs(b))


def mod_(a, b) -> int:
    """QBASIC MOD.

    Both operands are truncated toward zero. The result takes the sign of the
    dividend (first operand). Raises QBDivisionByZeroError if b == 0.
    """
    a = _truncate_to_int(a)
    b = _truncate_to_int(b)
    if b == 0:
        raise QBDivisionByZeroError()
    # Result sign follows dividend, magnitude uses truncated division.
    return a - idiv(a, b) * b


# ---------------------------------------------------------------------------
# 16-bit integer overflow checking
# ---------------------------------------------------------------------------


def int16(x) -> int:
    """Coerce *x* to a 16-bit signed integer, raising QBOverflowError on overflow.

    Use this wherever DEFINT A-Z arithmetic could exceed [-32768, 32767].
    Float inputs are truncated toward zero first (QBASIC implicit conversion).
    """
    v = _truncate_to_int(x)
    if v < _INT16_MIN or v > _INT16_MAX:
        raise QBOverflowError()
    return v


def int16_add(a: int, b: int) -> int:
    """16-bit signed addition with overflow check."""
    return int16(a + b)


def int16_sub(a: int, b: int) -> int:
    """16-bit signed subtraction with overflow check."""
    return int16(a - b)


def int16_mul(a: int, b: int) -> int:
    """16-bit signed multiplication with overflow check."""
    return int16(a * b)


# ---------------------------------------------------------------------------
# Single-precision (float32) emulation
# ---------------------------------------------------------------------------


def sng(x) -> float:
    """Round a Python float to single-precision (IEEE 754 float32).

    Use wherever the QBASIC source uses ! (single) or where 7-digit precision
    matters (e.g. PRINT of single-precision values, loop accumulators).
    """
    return struct.unpack("f", struct.pack("f", float(x)))[0]


# ---------------------------------------------------------------------------
# Absolute value (QBASIC ABS is the same for int/float)
# ---------------------------------------------------------------------------


def abs_(x):
    """QBASIC ABS() — works for both int and float."""
    return abs(x)
