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
    SerialReadError,
    SerialWriteError,
)
from samps import (
    SerialAsyncCommonInterface as SerialCommonInterface,
)

# **************************************************************************************


class TestSerialAsyncCommonInterface(unittest.IsolatedAsyncioTestCase):
    """
    Unit tests for SerialCommonInterface using a pseudo-TTY device:
    """

    async def asyncSetUp(self) -> None:
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
        await self.serial.open()

    async def asyncTearDown(self) -> None:
        """
        Close the serial interface and underlying file descriptors:
        """
        await self.serial.close()
        os.close(self.master_file_descriptor)
        os.close(self.slave_file_descriptor)

    async def test_context_manager_opens_and_closes(self) -> None:
        """
        Test that the context manager opens on enter and closes on exit:
        """
        async with SerialCommonInterface(
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

    async def test_is_open_and_is_closed(self) -> None:
        """
        Test the is_open and is_closed methods:
        """
        self.assertTrue(self.serial.is_open())
        self.assertFalse(self.serial.is_closed())
        await self.serial.close()
        self.assertFalse(self.serial.is_open())
        self.assertTrue(self.serial.is_closed())

    async def test_repr_contains_port_and_baudrate(self) -> None:
        """
        Test that __repr__ includes port and baudrate information:
        """
        representation = repr(self.serial)
        self.assertIn(self.slave_device_name, representation)
        self.assertIn("9600", representation)

    async def test_write_and_read_through_pty(self) -> None:
        """
        Test writing to the slave is readable from the master and vice versa:
        """
        data = b"hello-world"
        number_written = await self.serial.write(data)
        self.assertEqual(number_written, len(data))

        received = os.read(self.master_file_descriptor, len(data))
        self.assertEqual(received, data)

        os.write(self.master_file_descriptor, data)
        read_back = await self.serial.read(len(data))
        self.assertEqual(read_back, data)

    async def test_read_zero_length(self) -> None:
        """
        Test that reading zero bytes returns an empty bytes object:
        """
        self.assertEqual(await self.serial.read(0), b"")

    async def test_write_zero_length(self) -> None:
        """
        Test that writing zero bytes returns zero:
        """
        self.assertEqual(await self.serial.write(b""), 0)

    async def test_partial_write_retries(self) -> None:
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
            number_written = await self.serial.write(data)
            self.assertEqual(number_written, len(data))

            received = b""
            while len(received) < len(data):
                received += os.read(
                    self.master_file_descriptor, len(data) - len(received)
                )
            self.assertEqual(received, data)

    async def test_read_timeout_raises(self) -> None:
        """
        Test that read raises a SerialReadError after the timeout expires:
        """
        short_serial = SerialCommonInterface(
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
        await short_serial.open()
        start_time = time.time()
        with self.assertRaises(SerialReadError):
            await short_serial.read(1)
        self.assertGreaterEqual(time.time() - start_time, 0.1)
        await short_serial.close()

    async def test_constructor_without_params_uses_defaults(self) -> None:
        """
        Test that omitting params falls back to the default parameters:
        """
        serial = SerialCommonInterface(
            port=self.slave_device_name,
            baudrate=19200,
        )
        await serial.open()
        self.assertTrue(serial.is_open())
        # Default bytesize and parity come from default_serial_parameters:
        self.assertEqual(serial.bytesize, 8)
        self.assertEqual(serial.parity, "N")
        await serial.close()

    async def test_read_nontransient_error_raises(self) -> None:
        """
        Test that a non-transient OSError in read is wrapped in SerialReadError:
        """
        with unittest.mock.patch("os.read", side_effect=OSError(EINVAL, "bad")):
            with self.assertRaises(SerialReadError):
                await self.serial.read(1)

    async def test_write_nontransient_error_raises(self) -> None:
        """
        Test that a non-transient OSError in write is wrapped in SerialWriteError:
        """
        with unittest.mock.patch("os.write", side_effect=OSError(EINVAL, "bad")):
            with self.assertRaises(SerialWriteError):
                await self.serial.write(b"x")

    async def test_flush_before_and_after_open(self) -> None:
        """
        Test that flush works when open and raises when closed:
        """
        await self.serial.flush()
        await self.serial.close()
        with self.assertRaises(RuntimeError):
            await self.serial.flush()

    async def test_property_setters_apply_settings(self) -> None:
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

    async def test_baudrate_setter(self) -> None:
        """
        Test that setting baudrate updates internal state without error:
        """
        for raw in BAUDRATES:
            baudrate_value: BaudrateType = cast(BaudrateType, raw)
            self.serial.set_baudrate(baudrate_value)
            self.assertEqual(self.serial.baudrate, baudrate_value)

    async def test_set_port_updates_property(self) -> None:
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

    async def test_get_termios_attributes_structure(self) -> None:
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

    async def test_close_idempotent(self) -> None:
        """
        Test that calling close multiple times does not raise:
        """
        await self.serial.close()
        await self.serial.close()


# **************************************************************************************

if __name__ == "__main__":
    unittest.main()

# **************************************************************************************
