# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import unittest
from struct import pack
from typing import Any

from samps.crc import get_cyclic_redundancy_checksum

# **************************************************************************************


class TestCyclicRedundancyChecksum(unittest.TestCase):
    def test_crc8(self) -> None:
        data: bytes = b"123456789"
        crc = get_cyclic_redundancy_checksum(data, 8)
        self.assertEqual(crc, 0xF4)

    def test_crc16(self) -> None:
        data: bytes = b"123456789"
        crc = get_cyclic_redundancy_checksum(data, 16)
        self.assertEqual(crc, 0x4B37)

    def test_crc32(self) -> None:
        data: bytes = b"123456789"
        crc = get_cyclic_redundancy_checksum(data, 32)
        self.assertEqual(crc, 0xCBF43926)

    def test_bit_masking(self) -> None:
        data: bytes = bytes(range(256))
        crc = get_cyclic_redundancy_checksum(data, 8)
        self.assertTrue(0 <= crc <= 0xFF)

        crc = get_cyclic_redundancy_checksum(data, 16)
        self.assertTrue(0 <= crc <= 0xFFFF)

        crc = get_cyclic_redundancy_checksum(data, 32)
        self.assertTrue(0 <= crc <= 0xFFFFFFFF)

    def test_invalid_bits(self) -> None:
        bits: Any = 12

        with self.assertRaises(ValueError):
            _ = get_cyclic_redundancy_checksum(b"abc", bits)

    def test_empty_data(self) -> None:
        crc = get_cyclic_redundancy_checksum(b"", 8)
        self.assertEqual(crc, 0x00)

        crc = get_cyclic_redundancy_checksum(b"", 16)
        self.assertEqual(crc, 0xFFFF)

        crc = get_cyclic_redundancy_checksum(b"", 32)
        self.assertEqual(crc, 0x00000000)

    def test_number_of_bytes(self) -> None:
        crc = get_cyclic_redundancy_checksum(b"A", 8)
        bytes = pack("<H", crc)
        self.assertEqual(len(crc.to_bytes(2, "little")), len(bytes))


# **************************************************************************************

if __name__ == "__main__":
    unittest.main()

# **************************************************************************************
