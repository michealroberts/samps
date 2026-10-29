# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import os
import tty
import unittest
import unittest.mock
from errno import EINVAL, EIO

from samps import (
    BaseInterface,
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

        # Put the slave end into raw mode, as a USBTMC device has no line discipline,
        # so that the pseudo-TTY does not echo input or translate output:
        tty.setraw(self.slave_file_descriptor)

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

    def test_is_base_interface(self) -> None:
        """
        Test that USBTMCCommonInterface explicitly subclasses the BaseInterface protocol:
        """
        self.assertIn(BaseInterface, USBTMCCommonInterface.__mro__)
        self.assertTrue(issubclass(USBTMCCommonInterface, BaseInterface))
        self.assertIsInstance(self.serial, BaseInterface)

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
        self.assertEqual(written_back, query)

    def test_readline_retains_bytes_after_eol(self) -> None:
        """
        Test that bytes after the eol marker are retained for the next readline:
        """
        os.write(self.master_file_descriptor, b"first\nsecond\n")

        self.assertEqual(self.serial.readline(), b"first\n")
        self.assertEqual(self.serial.readline(), b"second\n")

    def test_read_returns_bytes_retained_by_readline(self) -> None:
        """
        Test that read returns bytes retained after the eol marker by readline:
        """
        os.write(self.master_file_descriptor, b"line\nXY")

        self.assertEqual(self.serial.readline(), b"line\n")
        self.assertEqual(self.serial.read(2), b"XY")

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

    def test_open_releases_file_descriptor_when_set_timeout_fails(self) -> None:
        """
        Test that open closes the file descriptor and is not open if set_timeout fails:
        """
        # Used to capture the file descriptor opened by open():
        original_open = os.open
        opened: list[int] = []

        def fake_open(path: str, flags: int) -> int:
            fd = original_open(path, flags)
            opened.append(fd)
            return fd

        serial = USBTMCCommonInterface(
            port=self.slave_device_name,
        )

        with unittest.mock.patch("os.open", new=fake_open):
            with unittest.mock.patch("samps.tmc.ioctl", side_effect=OSError(EIO, "io")):
                with self.assertRaises(RuntimeError):
                    serial.open()

        self.assertFalse(serial.is_open())
        self.assertEqual(len(opened), 1)

        # The file descriptor opened by open() must have been closed:
        with self.assertRaises(OSError):
            os.fstat(opened[0])

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
