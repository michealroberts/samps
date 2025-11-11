# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import os
import time
import unittest
import unittest.mock
from errno import EINVAL

from samps import (
    SerialReadError,
    SerialWriteError,
    USBTMCCommonInterface,
)

# **************************************************************************************


class TestTMCCommonInterface(unittest.TestCase):
    """
    Unit tests for TMCCommonInterface using a pseudo-TTY pair to simulate
    serial communication.
    """

    master_file_descriptor: int
    slave_file_descriptor: int
    slave_device_name: str
    serial: USBTMCCommonInterface

    def setUp(self) -> None:
        """
        Create a pseudo-file descriptor pair and open the serial interface on the slave end:
        """
        self.master_file_descriptor, self.slave_file_descriptor = os.openpty()
        self.slave_device_name = os.ttyname(self.slave_file_descriptor)

        self.serial = USBTMCCommonInterface(
            port=self.slave_device_name,
            params={
                "timeout": 0.5,
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
        with USBTMCCommonInterface(
            port=self.slave_device_name,
            params={
                "timeout": 0.1,
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

    def test_repr_contains_port_and_timeout(self) -> None:
        """
        Test that __repr__ includes port and timeout information:
        """
        representation = repr(self.serial)
        self.assertIn(self.slave_device_name, representation)

    def test_write_and_read(self) -> None:
        """
        Test writing to the slave is readable from the master and vice versa:
        """
        r_fd, w_fd = os.pipe()

        try:
            serial = USBTMCCommonInterface(
                port="/dev/fake",
                params={
                    "timeout": 0.5,
                },
            )
            serial._fd = w_fd
            serial._is_open = True

            data = b"hello"
            written = serial.write(data)
            self.assertEqual(written, len(data))

            # Read from pipe — simulating USBTMC bulk OUT endpoint:
            received = os.read(r_fd, len(data))
            self.assertEqual(received, data)
        finally:
            os.close(r_fd)
            os.close(w_fd)

    def test_ask(self) -> None:
        """
        Test the ask method for write followed by read:
        """
        query = b"hello-world\n"
        reply = b"echo: hello-world\n"

        # Write the reply from the master side so that readline() can consume it:
        os.write(self.master_file_descriptor, reply)

        # Perform the ask operation, which writes the query and reads the reply:
        response = self.serial.ask(query)
        self.assertEqual(response, reply)

        # Verify that the query was actually written out on the wire:
        written_back = os.read(self.master_file_descriptor, len(query))
        self.assertEqual(
            written_back.rstrip(b"\r\n"),
            query.rstrip(b"\r\n"),
        )

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
        short_serial = USBTMCCommonInterface(
            port=self.slave_device_name,
            params={
                "timeout": 0.1,
            },
        )
        short_serial.open()
        start_time = time.time()
        with self.assertRaises(SerialReadError):
            short_serial.read(1)
        self.assertGreaterEqual(time.time() - start_time, 0.1)
        short_serial.close()

    def test_constructor_without_params_uses_defaults(self) -> None:
        """
        Test that omitting params falls back to the default parameters:
        """
        serial = USBTMCCommonInterface(
            port=self.slave_device_name,
        )
        serial.open()
        self.assertTrue(serial.is_open())
        serial.close()

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
