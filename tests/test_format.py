"""Tests for qb_runtime.format — QBASIC string and number formatting."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qb_runtime.format import (
    qb_str,
    qb_str_single,
    val,
    left,
    right,
    mid,
    instr,
    space,
    string_,
    ucase,
    lcase,
    ltrim,
    rtrim,
    chr_,
    asc,
)


class TestQbStr(unittest.TestCase):
    """STR$ equivalent for integers and doubles."""

    def test_positive_integer(self):
        self.assertEqual(qb_str(42), " 42")
        self.assertEqual(qb_str(0), " 0")
        self.assertEqual(qb_str(1), " 1")

    def test_negative_integer(self):
        self.assertEqual(qb_str(-1), "-1")
        self.assertEqual(qb_str(-42), "-42")

    def test_positive_double(self):
        result = qb_str(3.14)
        self.assertTrue(result.startswith(" "))
        self.assertIn("3.14", result)

    def test_negative_double(self):
        result = qb_str(-3.14)
        self.assertTrue(result.startswith("-"))
        self.assertIn("3.14", result)

    def test_zero_double(self):
        self.assertEqual(qb_str(0.0), " 0")

    def test_large_double_exponential(self):
        result = qb_str(1e15)
        self.assertIn("E", result)

    def test_small_double_exponential(self):
        result = qb_str(0.001)
        # 0.001 is < 0.1, should be exponential
        self.assertIn("E", result)


class TestQbStrSingle(unittest.TestCase):
    """STR$ for single-precision floats."""

    def test_basic(self):
        result = qb_str_single(3.14)
        self.assertTrue(result.startswith(" "))

    def test_negative(self):
        result = qb_str_single(-2.5)
        self.assertTrue(result.startswith("-"))

    def test_zero(self):
        self.assertEqual(qb_str_single(0.0), " 0")


class TestVal(unittest.TestCase):
    """VAL — parse leading numeric portion."""

    def test_simple_integer(self):
        self.assertEqual(val("42"), 42.0)
        self.assertEqual(val(" 42"), 42.0)

    def test_negative(self):
        self.assertEqual(val("-7"), -7.0)

    def test_decimal(self):
        self.assertEqual(val("3.14"), 3.14)

    def test_leading_dot(self):
        self.assertEqual(val(".5"), 0.5)

    def test_scientific(self):
        self.assertEqual(val("1E3"), 1000.0)
        self.assertEqual(val("2.5E-2"), 0.025)

    def test_trailing_text(self):
        self.assertEqual(val("42hello"), 42.0)
        self.assertEqual(val("3.14xyz"), 3.14)

    def test_no_number(self):
        self.assertEqual(val("hello"), 0.0)
        self.assertEqual(val(""), 0.0)

    def test_hex(self):
        self.assertEqual(val("&HFF"), 255.0)
        self.assertEqual(val("&H10"), 16.0)

    def test_octal(self):
        self.assertEqual(val("&O10"), 8.0)
        self.assertEqual(val("&O77"), 63.0)

    def test_spaces(self):
        self.assertEqual(val("   42"), 42.0)
        self.assertEqual(val("  "), 0.0)


class TestLeft(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(left("Hello", 3), "Hel")
        self.assertEqual(left("Hello", 10), "Hello")

    def test_zero(self):
        self.assertEqual(left("Hello", 0), "")

    def test_empty(self):
        self.assertEqual(left("", 5), "")


class TestRight(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(right("Hello", 3), "llo")
        self.assertEqual(right("Hello", 10), "Hello")

    def test_zero(self):
        self.assertEqual(right("Hello", 0), "")

    def test_empty(self):
        self.assertEqual(right("", 5), "")


class TestMid(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(mid("Hello", 2, 3), "ell")

    def test_1based(self):
        self.assertEqual(mid("Hello", 1, 1), "H")
        self.assertEqual(mid("Hello", 5, 1), "o")

    def test_no_length(self):
        self.assertEqual(mid("Hello", 3), "llo")

    def test_start_beyond_end(self):
        self.assertEqual(mid("Hello", 10), "")

    def test_zero_length(self):
        self.assertEqual(mid("Hello", 1, 0), "")


class TestInstr(unittest.TestCase):
    def test_found(self):
        self.assertEqual(instr(1, "Hello World", "World"), 7)

    def test_not_found(self):
        self.assertEqual(instr(1, "Hello", "xyz"), 0)

    def test_start_position(self):
        # 'o' at pos 5 ("Hello"), pos 8 ("World"); start=6 skips the first one
        self.assertEqual(instr(6, "Hello World", "o"), 8)

    def test_at_start(self):
        self.assertEqual(instr(1, "Hello", "H"), 1)

    def test_empty_substring(self):
        # QBASIC: INSTR with empty substring returns start position
        self.assertEqual(instr(1, "Hello", ""), 1)


class TestSpace(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(space(5), "     ")
        self.assertEqual(space(0), "")
        self.assertEqual(space(-1), "")


class TestString(unittest.TestCase):
    def test_char(self):
        self.assertEqual(string_(3, "A"), "AAA")

    def test_ascii_code(self):
        self.assertEqual(string_(3, 65), "AAA")

    def test_zero(self):
        self.assertEqual(string_(0, "X"), "")


class TestUcase(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(ucase("hello"), "HELLO")
        self.assertEqual(ucase("Hello World"), "HELLO WORLD")


class TestLcase(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(lcase("HELLO"), "hello")


class TestLtrim(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(ltrim("  hello"), "hello")
        self.assertEqual(ltrim("hello"), "hello")
        self.assertEqual(ltrim("  "), "")


class TestRtrim(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(rtrim("hello  "), "hello")
        self.assertEqual(rtrim("hello"), "hello")


class TestChr(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(chr_(65), "A")
        self.assertEqual(chr_(13), "\r")
        self.assertEqual(chr_(0), "\x00")


class TestAsc(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(asc("A"), 65)
        self.assertEqual(asc("Hello"), 72)

    def test_empty(self):
        self.assertEqual(asc(""), 0)


if __name__ == "__main__":
    unittest.main()
