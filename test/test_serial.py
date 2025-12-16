# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import os
import termios
import time
import unittest
import unittest.mock
from errno import EINVAL
from typing import cast

from samps import (
    BAUDRATES,
    BaudrateType,
    SerialCommonInterface,
    SerialReadError,
    SerialWriteError,
)

# **************************************************************************************


class TestSerialCommonInterface(unittest.TestCase):
    """
    Unit tests for SerialCommonInterface using a pseudo-TTY device:
    """

    master_file_descriptor: int
    slave_file_descriptor: int
    slave_device_name: str
    serial: SerialCommonInterface

    def setUp(self) -> None:
        """
        Create a pseudo-TTY pair and open the serial interface on the slave end:
        """
        self.master_file_descriptor, self.slave_file_descriptor = os.openpty()
        self.slave_device_name = os.ttyname(self.slave_file_descriptor)

        self.serial = SerialCommonInterface(
            port=self.slave_device_name,
            baudrate=9600,
            params={
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "timeout": 0.5,
                "xonxoff": False,
                "rtscts": False,
            },
        )
        self.serial.open()

    def tearDown(self) -> None:
        """
        Close the serial interface and underlying file descriptors:
        """
        self.serial.close()
        os.close(self.master_file_descriptor)
        os.close(self.slave_file_descriptor)

    def test_context_manager_opens_and_closes(self) -> None:
        """
        Test that the context manager opens on enter and closes on exit:
        """
        with SerialCommonInterface(
            port=self.slave_device_name,
            baudrate=9600,
            params={
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "timeout": 0.1,
                "xonxoff": False,
                "rtscts": False,
            },
        ) as serial_context:
            self.assertTrue(serial_context.is_open())
        self.assertFalse(serial_context.is_open())

    def test_is_open_and_is_closed(self) -> None:
        """
        Test the is_open and is_closed methods:
        """
        self.assertTrue(self.serial.is_open())
        self.assertFalse(self.serial.is_closed())
        self.serial.close()
        self.assertFalse(self.serial.is_open())
        self.assertTrue(self.serial.is_closed())

    def test_repr_contains_port_and_baudrate(self) -> None:
        """
        Test that __repr__ includes port and baudrate information:
        """
        representation = repr(self.serial)
        self.assertIn(self.slave_device_name, representation)
        self.assertIn("9600", representation)

    def test_write_and_read_through_pty(self) -> None:
        """
        Test writing to the slave is readable from the master and vice versa:
        """
        data = b"hello-world"
        number_written = self.serial.write(data)
        self.assertEqual(number_written, len(data))

        received = os.read(self.master_file_descriptor, len(data))
        self.assertEqual(received, data)

        os.write(self.master_file_descriptor, data)
        read_back = self.serial.read(len(data))
        self.assertEqual(read_back, data)

    def test_ask_through_pty(self) -> None:
        """
        Test the ask method for write followed by read:
        """
        query = b"hello-world\n"
        reply = b"echo: hello-world\n"

        os.write(self.master_file_descriptor, reply)

        response = self.serial.ask(query)
        self.assertEqual(response, reply)
        written_back = os.read(self.master_file_descriptor, len(query))
        self.assertEqual(written_back, query)

    def test_read_zero_length(self) -> None:
        """
        Test that reading zero bytes returns an empty bytes object:
        """
        self.assertEqual(self.serial.read(0), b"")

    def test_write_zero_length(self) -> None:
        """
        Test that writing zero bytes returns zero:
        """
        self.assertEqual(self.serial.write(b""), 0)

    def test_partial_write_retries(self) -> None:
        """
        Test that write retries on partial writes until all bytes are written:
        """
        # Used to simulate a partial write condition on the first call to fake_write:
        original_write = os.write
        calls: list[int] = []

        def fake_write(fd: int, buf: bytes) -> int:
            if not calls:
                calls.append(1)
                return original_write(fd, buf[: len(buf) // 2])
            return original_write(fd, buf)

        with unittest.mock.patch("os.write", new=fake_write):
            data = b"ABCDEFGH"
            number_written = self.serial.write(data)
            self.assertEqual(number_written, len(data))

            received = b""
            while len(received) < len(data):
                received += os.read(
                    self.master_file_descriptor, len(data) - len(received)
                )
            self.assertEqual(received, data)

    def test_read_timeout_raises(self) -> None:
        """
        Test that read raises a SerialReadError after the timeout expires:
        """
        serial = SerialCommonInterface(
            port=self.slave_device_name,
            baudrate=9600,
            params={
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "timeout": 0.1,
                "xonxoff": False,
                "rtscts": False,
            },
        )
        serial.open()
        start_time = time.time()

        with self.assertRaises(SerialReadError):
            serial.read(1)

        self.assertGreaterEqual(time.time() - start_time, 0.1)
        serial.close()

    def test_constructor_without_params_uses_defaults(self) -> None:
        """
        Test that omitting params falls back to the default parameters:
        """
        serial2 = SerialCommonInterface(
            port=self.slave_device_name,
            baudrate=19200,
        )
        serial2.open()
        self.assertTrue(serial2.is_open())
        # Default bytesize and parity come from default_serial_parameters
        self.assertEqual(serial2.bytesize, 8)
        self.assertEqual(serial2.parity, "N")
        serial2.close()

    def test_read_nontransient_error_raises(self) -> None:
        """
        Test that a non-transient OSError in read is wrapped in SerialReadError:
        """
        with unittest.mock.patch("os.read", side_effect=OSError(EINVAL, "bad")):
            with self.assertRaises(SerialReadError):
                self.serial.read(1)

    def test_write_nontransient_error_raises(self) -> None:
        """
        Test that a non-transient OSError in write is wrapped in SerialWriteError:
        """
        with unittest.mock.patch("os.write", side_effect=OSError(EINVAL, "bad")):
            with self.assertRaises(SerialWriteError):
                self.serial.write(b"x")

    def test_flush_before_and_after_open(self) -> None:
        """
        Test that flush works when open and raises when closed:
        """
        self.serial.flush()
        self.serial.close()
        with self.assertRaises(RuntimeError):
            self.serial.flush()

    def test_property_setters_apply_settings(self) -> None:
        """
        Test that setting bytesize and parity updates internal state:
        """
        with unittest.mock.patch.object(
            self.serial, "_configure_tty_settings", lambda attrs: None
        ):
            for size in (5, 6, 7, 8):
                self.serial.set_bytesize(size)
                self.assertEqual(self.serial.bytesize, size)
            for parity_value in ("N", "E", "O"):
                self.serial.set_parity(parity_value)
                self.assertEqual(self.serial.parity, parity_value)

    def test_baudrate_setter(self) -> None:
        """
        Test that setting baudrate updates internal state without error:
        """
        for raw in BAUDRATES:
            baudrate_value: BaudrateType = cast(BaudrateType, raw)
            self.serial.set_baudrate(baudrate_value)
            self.assertEqual(self.serial.baudrate, baudrate_value)

    def test_set_port_updates_property(self) -> None:
        """
        Test that set_port changes the port property and reapplies settings:
        """
        master, slave = os.openpty()
        name = os.ttyname(slave)
        try:
            self.serial.set_port(name)
            self.assertEqual(self.serial.port, name)
        finally:
            os.close(master)
            os.close(slave)

    def test_get_termios_attributes_structure(self) -> None:
        """
        Test that _get_termios_attributes returns a correctly structured dict:
        """
        termios_attributes = self.serial._get_termios_attributes()
        self.assertIsInstance(termios_attributes, dict)
        expected_keys = {
            "iflag",
            "oflag",
            "cflag",
            "lflag",
            "ispeed",
            "ospeed",
            "control_chars",
        }
        self.assertEqual(set(termios_attributes.keys()), expected_keys)
        self.assertIsInstance(termios_attributes["control_chars"], list)
        self.assertGreaterEqual(
            len(termios_attributes["control_chars"]), termios.VTIME + 1
        )

    def test_close_idempotent(self) -> None:
        """
        Test that calling close multiple times does not raise:
        """
        self.serial.close()
        self.serial.close()


# **************************************************************************************

if __name__ == "__main__":
    unittest.main()

# **************************************************************************************
