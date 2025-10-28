# **************************************************************************************
#
# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts
#
# **************************************************************************************

import unittest

from samps.utilities import hex_to_int, int_to_hex

# **************************************************************************************


class TestIntToHex(unittest.TestCase):
    """
    Unit tests for int_to_hex converting 0..0xFFFFFF into a fixed-length 3-byte tuple (big endian).
    """

    def test_returns_tuple_of_three_bytes(self) -> None:
        """
        The function must return a 3-tuple of ints in the range 0..255.
        """
        result = int_to_hex(0x123456)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        for b in result:
            self.assertIsInstance(b, int)
            self.assertGreaterEqual(b, 0)
            self.assertLessEqual(b, 255)

    def test_boundaries(self) -> None:
        """
        Check exact outputs for boundary values 0x000000, 0x000001, 0xFFFFFF.
        """
        self.assertEqual(int_to_hex(0x000000), (0x00, 0x00, 0x00))
        self.assertEqual(int_to_hex(0x000001), (0x00, 0x00, 0x01))
        self.assertEqual(int_to_hex(0xFFFFFF), (0xFF, 0xFF, 0xFF))

    def test_known_patterns(self) -> None:
        """
        Validate known conversions for common patterns.
        """
        self.assertEqual(int_to_hex(0x123456), (0x12, 0x34, 0x56))
        self.assertEqual(int_to_hex(0x010203), (0x01, 0x02, 0x03))
        self.assertEqual(int_to_hex(0x00FF00), (0x00, 0xFF, 0x00))
        self.assertEqual(int_to_hex(0xABCD00), (0xAB, 0xCD, 0x00))

    def test_type_validation_rejects_non_int(self) -> None:
        """
        Non-integer inputs (including bool) must raise TypeError.
        """
        with self.assertRaises(TypeError):
            int_to_hex(True)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            int_to_hex(False)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            int_to_hex(3.14)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            int_to_hex("255")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            int_to_hex(None)  # type: ignore[arg-type]

    def test_range_validation(self) -> None:
        """
        Values outside 0..0xFFFFFF must raise ValueError.
        """
        with self.assertRaises(ValueError):
            int_to_hex(-1)
        with self.assertRaises(ValueError):
            int_to_hex(0x1000000)

    def test_idempotent_rounding_behavior(self) -> None:
        """
        Ensure there is no implicit rounding or truncation beyond the 24-bit mask.
        """
        self.assertEqual(int_to_hex(255), (0x00, 0x00, 0xFF))
        self.assertNotEqual(int_to_hex(255), (0x00, 0x01, 0x00))
        self.assertEqual(int_to_hex(256), (0x00, 0x01, 0x00))


# **************************************************************************************


class TestHexToInt(unittest.TestCase):
    """
    Unit tests for hex_to_int converting a fixed-length 3-byte tuple (big endian) into 0..0xFFFFFF.
    """

    def test_returns_integer(self) -> None:
        """
        The function must return an integer in the range 0..255.
        """
        result = hex_to_int((0x12, 0x34, 0x56))
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 0x123456)

    def test_boundaries(self) -> None:
        """
        Check exact outputs for boundary values (0x00,0x00,0x00), (0x00,0x00,0x01), (0xFF,0xFF,0xFF).
        """
        self.assertEqual(hex_to_int((0x00, 0x00, 0x00)), 0x000000)
        self.assertEqual(hex_to_int((0x00, 0x00, 0x01)), 0x000001)
        self.assertEqual(hex_to_int((0xFF, 0xFF, 0xFF)), 0xFFFFFF)

    def test_known_patterns(self) -> None:
        """
        Validate known conversions for common patterns.
        """
        self.assertEqual(hex_to_int((0x12, 0x34, 0x56)), 0x123456)
        self.assertEqual(hex_to_int((0x01, 0x02, 0x03)), 0x010203)
        self.assertEqual(hex_to_int((0x00, 0xFF, 0x00)), 0x00FF00)
        self.assertEqual(hex_to_int((0xAB, 0xCD, 0x00)), 0xABCD00)

    def test_type_validation_rejects_non_tuple(self) -> None:
        """
        Non-tuple inputs must raise TypeError.
        """
        with self.assertRaises(TypeError):
            hex_to_int([0x00, 0x00, 0x00])  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            hex_to_int(True)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            hex_to_int(False)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            hex_to_int("0x000000")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            hex_to_int(123456)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            hex_to_int(None)  # type: ignore[arg-type]

    def test_range_validation(self) -> None:
        """
        Tuples with values outside 0..255 must raise ValueError.
        """
        with self.assertRaises(ValueError):
            hex_to_int((256, 0, 0))
        with self.assertRaises(ValueError):
            hex_to_int((0, -1, 0))
        with self.assertRaises(ValueError):
            hex_to_int((0, 0, 300))

    def test_idempotent_rounding_behavior(self) -> None:
        """
        Ensure there is no implicit rounding or truncation beyond the 8-bit mask per byte.
        """
        self.assertEqual(hex_to_int((0x00, 0x00, 0xFF)), 255)
        self.assertNotEqual(hex_to_int((0x00, 0x01, 0x00)), 255)
        self.assertEqual(hex_to_int((0x00, 0x01, 0x00)), 256)


# **************************************************************************************

if __name__ == "__main__":
    unittest.main()

# **************************************************************************************
