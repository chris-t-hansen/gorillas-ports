"""Tests for qb_runtime.qbmath — QBASIC numeric semantics."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qb_runtime.qbmath import (
    cint,
    int_,
    fix_,
    idiv,
    mod_,
    int16,
    int16_add,
    int16_sub,
    int16_mul,
    sng,
    QBOverflowError,
    QBDivisionByZeroError,
)


class TestCint(unittest.TestCase):
    """CINT uses banker's rounding (round half to even)."""

    def test_exact_integers(self):
        self.assertEqual(cint(0), 0)
        self.assertEqual(cint(1), 1)
        self.assertEqual(cint(-1), -1)
        self.assertEqual(cint(100), 100)

    def test_round_down(self):
        self.assertEqual(cint(0.4), 0)
        self.assertEqual(cint(1.4), 1)
        self.assertEqual(cint(2.3), 2)
        self.assertEqual(cint(-0.4), 0)
        self.assertEqual(cint(-1.4), -1)

    def test_round_up(self):
        self.assertEqual(cint(0.6), 1)
        self.assertEqual(cint(1.7), 2)
        self.assertEqual(cint(-0.6), -1)
        self.assertEqual(cint(-1.7), -2)

    def test_bankers_rounding_half_to_even(self):
        # .5 rounds to nearest even
        self.assertEqual(cint(0.5), 0)  # 0 is even
        self.assertEqual(cint(1.5), 2)  # 2 is even
        self.assertEqual(cint(2.5), 2)  # 2 is even
        self.assertEqual(cint(3.5), 4)  # 4 is even
        self.assertEqual(cint(4.5), 4)  # 4 is even

    def test_bankers_rounding_negative(self):
        self.assertEqual(cint(-0.5), 0)
        self.assertEqual(cint(-1.5), -2)
        self.assertEqual(cint(-2.5), -2)
        self.assertEqual(cint(-3.5), -4)

    def test_large_values(self):
        self.assertEqual(cint(32767.4), 32767)
        self.assertEqual(cint(-32768.4), -32768)


class TestInt(unittest.TestCase):
    """INT floors toward negative infinity."""

    def test_positive(self):
        self.assertEqual(int_(3.7), 3)
        self.assertEqual(int_(3.0), 3)
        self.assertEqual(int_(0.9), 0)

    def test_negative(self):
        self.assertEqual(int_(-3.7), -4)
        self.assertEqual(int_(-3.0), -3)
        self.assertEqual(int_(-0.1), -1)

    def test_zero(self):
        self.assertEqual(int_(0.0), 0)


class TestFix(unittest.TestCase):
    """FIX truncates toward zero."""

    def test_positive(self):
        self.assertEqual(fix_(3.7), 3)
        self.assertEqual(fix_(3.999), 3)
        self.assertEqual(fix_(0.9), 0)

    def test_negative(self):
        self.assertEqual(fix_(-3.7), -3)
        self.assertEqual(fix_(-3.999), -3)
        self.assertEqual(fix_(-0.9), 0)

    def test_zero(self):
        self.assertEqual(fix_(0.0), 0)


class TestIdiv(unittest.TestCase):
    """Integer division truncates toward zero."""

    def test_positive(self):
        self.assertEqual(idiv(7, 2), 3)
        self.assertEqual(idiv(10, 3), 3)
        self.assertEqual(idiv(100, 10), 10)

    def test_negative_dividend(self):
        self.assertEqual(idiv(-7, 2), -3)  # not -4 (Python // gives -4)
        self.assertEqual(idiv(-10, 3), -3)

    def test_negative_divisor(self):
        self.assertEqual(idiv(7, -2), -3)
        self.assertEqual(idiv(-7, -2), 3)

    def test_zero_dividend(self):
        self.assertEqual(idiv(0, 5), 0)

    def test_division_by_zero(self):
        with self.assertRaises(QBDivisionByZeroError):
            idiv(5, 0)

    def test_float_operands_truncated(self):
        # QBASIC truncates operands toward zero before dividing
        self.assertEqual(idiv(7.9, 2.9), 3)  # 7 \ 2 = 3
        self.assertEqual(idiv(7.9, 2.1), 3)  # 7 \ 2 = 3


class TestMod(unittest.TestCase):
    """MOD: result takes sign of dividend, operands truncated toward zero."""

    def test_positive(self):
        self.assertEqual(mod_(7, 3), 1)
        self.assertEqual(mod_(10, 5), 0)
        self.assertEqual(mod_(10, 3), 1)

    def test_negative_dividend(self):
        # QBASIC: (-5) MOD 3 = -2  (Python: -5 % 3 = 1)
        self.assertEqual(mod_(-5, 3), -2)
        self.assertEqual(mod_(-7, 2), -1)

    def test_negative_divisor(self):
        # QBASIC: 5 MOD -3 = 2  (Python: 5 % -3 = -1)
        self.assertEqual(mod_(5, -3), 2)
        self.assertEqual(mod_(-5, -3), -2)

    def test_zero_dividend(self):
        self.assertEqual(mod_(0, 5), 0)

    def test_division_by_zero(self):
        with self.assertRaises(QBDivisionByZeroError):
            mod_(5, 0)

    def test_float_operands_truncated(self):
        self.assertEqual(mod_(7.9, 3.9), 1)  # 7 MOD 3 = 1


class TestInt16(unittest.TestCase):
    """16-bit signed integer overflow checking."""

    def test_valid_range(self):
        self.assertEqual(int16(0), 0)
        self.assertEqual(int16(32767), 32767)
        self.assertEqual(int16(-32768), -32768)

    def test_overflow_high(self):
        with self.assertRaises(QBOverflowError):
            int16(32768)

    def test_overflow_low(self):
        with self.assertRaises(QBOverflowError):
            int16(-32769)

    def test_large_overflow(self):
        with self.assertRaises(QBOverflowError):
            int16(100000)

    def test_float_truncation(self):
        self.assertEqual(int16(3.7), 3)
        self.assertEqual(int16(-3.7), -3)

    def test_arithmetic_overflow(self):
        with self.assertRaises(QBOverflowError):
            int16_add(32767, 1)
        with self.assertRaises(QBOverflowError):
            int16_sub(-32768, 1)
        with self.assertRaises(QBOverflowError):
            int16_mul(200, 200)

    def test_arithmetic_valid(self):
        self.assertEqual(int16_add(100, 200), 300)
        self.assertEqual(int16_sub(100, 200), -100)
        self.assertEqual(int16_mul(100, 200), 20000)


class TestSng(unittest.TestCase):
    """Single-precision (float32) rounding."""

    def test_exact_values(self):
        self.assertEqual(sng(0.0), 0.0)
        self.assertEqual(sng(1.0), 1.0)
        self.assertEqual(sng(-1.0), -1.0)

    def test_precision_loss(self):
        # 1/3 in float32 has limited precision
        result = sng(1.0 / 3.0)
        self.assertAlmostEqual(result, 0.3333333, places=7)

    def test_pi(self):
        # float32 pi ≈ 3.1415927
        result = sng(3.141592653589793)
        self.assertAlmostEqual(result, 3.1415927, places=6)

    def test_integer_passthrough(self):
        self.assertEqual(sng(42), 42.0)


if __name__ == "__main__":
    unittest.main()
