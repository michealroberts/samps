# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import os
import sys
import termios
import unittest
from typing import List, get_args

from samps import (
    BAUDRATE_LOOKUP_FLAGS,
    BAUDRATES,
    BaudrateType,
    SerialAsyncCommonInterface,
    SerialCommonInterface,
)

# **************************************************************************************

EXPECTED_BAUDRATES: List[int] = [
    0,
    50,
    75,
    110,
    134,
    150,
    200,
    300,
    600,
    1200,
    1800,
    2400,
    4800,
    9600,
    19200,
    38400,
    57600,
    115200,
    230400,
]

# **************************************************************************************

LINUX_BAUDRATES: List[int] = [
    460800,
    500000,
    576000,
    921600,
    1000000,
    1152000,
    1500000,
    2000000,
    2500000,
    3000000,
    3500000,
    4000000,
]

# **************************************************************************************


class TestBaudrates(unittest.TestCase):
    def test_baudrate_type_contains_all_expected_rates(self) -> None:
        self.assertEqual(
            list(get_args(BaudrateType)), EXPECTED_BAUDRATES + LINUX_BAUDRATES
        )

    @unittest.skipUnless(sys.platform == "linux", "Linux-only baud rates")
    def test_lookup_flags_contains_all_linux_rates(self) -> None:
        self.assertEqual(
            list(BAUDRATE_LOOKUP_FLAGS.keys()), EXPECTED_BAUDRATES + LINUX_BAUDRATES
        )

    @unittest.skipIf(sys.platform == "linux", "Non-Linux platforms only")
    def test_lookup_flags_excludes_linux_rates(self) -> None:
        self.assertEqual(list(BAUDRATE_LOOKUP_FLAGS.keys()), EXPECTED_BAUDRATES)

    def test_baudrates_match_lookup_flags(self) -> None:
        self.assertEqual(BAUDRATES, list(BAUDRATE_LOOKUP_FLAGS.values()))

    def test_lookup_flag_resolves_to_termios_constant(self) -> None:
        for rate, flag in BAUDRATE_LOOKUP_FLAGS.items():
            with self.subTest(rate=rate):
                self.assertEqual(flag, getattr(termios, f"B{rate}"))


# **************************************************************************************


class TestSerialCommonInterfaceBaudrates(unittest.TestCase):
    master_file_descriptor: int
    slave_file_descriptor: int
    slave_device_name: str

    def setUp(self) -> None:
        self.master_file_descriptor, self.slave_file_descriptor = os.openpty()
        self.slave_device_name = os.ttyname(self.slave_file_descriptor)

    def tearDown(self) -> None:
        os.close(self.master_file_descriptor)
        os.close(self.slave_file_descriptor)

    def test_accepts_all_baudrates(self) -> None:
        for rate in BAUDRATE_LOOKUP_FLAGS:
            with self.subTest(rate=rate):
                serial = SerialCommonInterface(
                    port=self.slave_device_name,
                    baudrate=rate,
                )
                self.assertEqual(serial.baudrate, rate)

    @unittest.skipIf(sys.platform == "linux", "Non-Linux platforms only")
    def test_rejects_linux_baudrates(self) -> None:
        for rate in LINUX_BAUDRATES:
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    SerialCommonInterface(
                        port=self.slave_device_name,
                        baudrate=rate,  # type: ignore[arg-type]
                    )

    def test_rejects_invalid_baudrate(self) -> None:
        with self.assertRaises(ValueError):
            SerialCommonInterface(
                port=self.slave_device_name,
                baudrate=12345,  # type: ignore[arg-type]
            )

    def test_invalid_baudrate_error_lists_baudrates(self) -> None:
        with self.assertRaises(ValueError) as context:
            SerialCommonInterface(
                port=self.slave_device_name,
                baudrate=12345,  # type: ignore[arg-type]
            )

        self.assertIn(str(list(BAUDRATE_LOOKUP_FLAGS)), str(context.exception))

    def test_async_invalid_baudrate_error_lists_baudrates(self) -> None:
        with self.assertRaises(ValueError) as context:
            SerialAsyncCommonInterface(
                port=self.slave_device_name,
                baudrate=12345,  # type: ignore[arg-type]
            )

        self.assertIn(str(list(BAUDRATE_LOOKUP_FLAGS)), str(context.exception))

    def test_opens_at_all_baudrates(self) -> None:
        for rate in BAUDRATE_LOOKUP_FLAGS:
            with self.subTest(rate=rate):
                serial = SerialCommonInterface(
                    port=self.slave_device_name,
                    baudrate=rate,
                )
                serial.open()
                try:
                    self.assertTrue(serial.is_open())
                finally:
                    serial.close()


# **************************************************************************************

if __name__ == "__main__":
    unittest.main()

# **************************************************************************************
