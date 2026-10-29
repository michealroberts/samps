# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import asyncio
import os
import struct
import termios
import threading
import time
import unittest
import unittest.mock
from errno import EINVAL, ENOTTY
from typing import cast

from samps import (
    BAUDRATE_LOOKUP_FLAGS,
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

    async def test_repr_uses_async_class_name(self) -> None:
        """
        Test that __repr__ names the asynchronous interface class:
        """
        representation = repr(self.serial)
        self.assertTrue(representation.startswith("SerialAsyncCommonInterface("))

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

    async def test_readline_retains_bytes_after_eol(self) -> None:
        """
        Test that bytes after the eol marker are retained for the next readline:
        """
        os.write(self.master_file_descriptor, b"first\nsecond\n")

        self.assertEqual(await self.serial.readline(), b"first\n")
        self.assertEqual(await self.serial.readline(), b"second\n")

    async def test_readline_matches_eol_split_across_reads(self) -> None:
        """
        Test that readline matches an eol marker split across two reads:
        """
        with unittest.mock.patch("os.read", side_effect=[b"first\r", b"\nsecond"]):
            self.assertEqual(await self.serial.readline(eol=b"\r\n"), b"first\r\n")

        self.assertEqual(await self.serial.read(6), b"second")

    async def test_read_returns_bytes_retained_by_readline(self) -> None:
        """
        Test that read returns bytes retained after the eol marker by readline:
        """
        os.write(self.master_file_descriptor, b"line\nXY")

        self.assertEqual(await self.serial.readline(), b"line\n")
        self.assertEqual(await self.serial.read(2), b"XY")

    async def test_close_discards_bytes_retained_by_readline(self) -> None:
        """
        Test that close discards bytes retained after the eol marker by readline:
        """
        os.write(self.master_file_descriptor, b"first\nsecond\n")

        self.assertEqual(await self.serial.readline(), b"first\n")
        await self.serial.close()
        await self.serial.open()

        with self.assertRaises(SerialReadError):
            await self.serial.readline()

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

    async def test_read_retries_on_empty_read(self) -> None:
        """
        Test that read keeps waiting for data when the port returns no bytes:
        """
        # Make the port readable, so the wait after the empty read returns at once:
        os.write(self.master_file_descriptor, b"x")

        with unittest.mock.patch("os.read", side_effect=[b"", b"x"]):
            self.assertEqual(await self.serial.read(1), b"x")

    async def test_readline_retries_on_empty_read(self) -> None:
        """
        Test that readline keeps waiting for data when the port returns no bytes:
        """
        # Make the port readable, so the wait after the empty read returns at once:
        os.write(self.master_file_descriptor, b"hello\n")

        with unittest.mock.patch("os.read", side_effect=[b"", b"hello\n"]):
            self.assertEqual(await self.serial.readline(), b"hello\n")

    async def test_read_does_not_block_event_loop(self) -> None:
        """
        Test that read waits for data without blocking the event loop:
        """

        async def write_later() -> None:
            await asyncio.sleep(0.1)
            os.write(self.master_file_descriptor, b"x")

        data, _ = await asyncio.gather(self.serial.read(1), write_later())
        self.assertEqual(data, b"x")

    async def test_readline_does_not_block_event_loop(self) -> None:
        """
        Test that readline waits for data without blocking the event loop:
        """

        async def write_later() -> None:
            await asyncio.sleep(0.1)
            os.write(self.master_file_descriptor, b"hello\n")

        line, _ = await asyncio.gather(self.serial.readline(), write_later())
        self.assertEqual(line, b"hello\n")

    async def test_write_does_not_block_event_loop(self) -> None:
        """
        Test that write waits for the port to drain without blocking the event loop:
        """
        data = b"x" * 65536
        received = bytearray()
        ticks = 0

        # Drain the master side slowly, so that the slave side fills up and blocks:
        def drain() -> None:
            while len(received) < len(data):
                received.extend(os.read(self.master_file_descriptor, 1024))
                time.sleep(0.001)

        # Count how often the event loop gets to run other tasks during the write:
        async def tick() -> None:
            nonlocal ticks
            while True:
                ticks += 1
                await asyncio.sleep(0)

        thread = threading.Thread(target=drain, daemon=True)
        thread.start()
        ticker = asyncio.create_task(tick())

        try:
            self.assertEqual(await self.serial.write(data), len(data))
        finally:
            ticker.cancel()
            thread.join(timeout=5)

        self.assertGreater(ticks, 0)
        self.assertEqual(bytes(received), data)

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

    async def test_open_releases_file_descriptor_when_configure_fails(self) -> None:
        """
        Test that open closes the file descriptor and is not open if the port is not a TTY:
        """
        # Used to capture the file descriptor opened by open():
        original_open = os.open
        opened: list[int] = []

        def fake_open(path: str, flags: int) -> int:
            fd = original_open(path, flags)
            opened.append(fd)
            return fd

        serial = SerialCommonInterface(
            port="/dev/null",
            baudrate=9600,
        )

        with unittest.mock.patch("os.open", new=fake_open):
            with self.assertRaises(termios.error):
                await serial.open()

        self.assertFalse(serial.is_open())
        self.assertIsNone(serial._fd)
        self.assertEqual(len(opened), 1)

        # The file descriptor opened by open() must have been closed:
        with self.assertRaises(OSError):
            os.fstat(opened[0])

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

    async def test_flush_does_not_block_event_loop(self) -> None:
        """
        Test that flush waits for the output to drain without blocking the event loop:
        """
        ticks = 0

        # Simulate a slow drain of the output buffer by the serial device:
        def slow_tcdrain(fd: int) -> None:
            time.sleep(0.1)

        # Count how often the event loop gets to run other tasks during the flush:
        async def tick() -> None:
            nonlocal ticks
            while True:
                ticks += 1
                await asyncio.sleep(0)

        ticker = asyncio.create_task(tick())

        try:
            with unittest.mock.patch("samps.asynchronous.tcdrain", new=slow_tcdrain):
                await self.serial.flush()
        finally:
            ticker.cancel()

        self.assertGreater(ticks, 0)

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
        for raw in BAUDRATE_LOOKUP_FLAGS:
            baudrate_value: BaudrateType = cast(BaudrateType, raw)
            self.serial.set_baudrate(baudrate_value)
            self.assertEqual(self.serial.baudrate, baudrate_value)

    async def test_set_baudrate_rejects_invalid_baudrate(self) -> None:
        """
        Test that set_baudrate raises ValueError and leaves the baudrate unchanged:
        """
        before = termios.tcgetattr(self.slave_file_descriptor)

        with self.assertRaises(ValueError):
            self.serial.set_baudrate(12345)  # type: ignore[arg-type]

        self.assertEqual(self.serial.baudrate, 9600)

        after = termios.tcgetattr(self.slave_file_descriptor)
        # The input and output speeds of the port must not have been reconfigured:
        self.assertEqual(after[4:6], before[4:6])

    async def test_configure_tty_settings_rejects_unsupported_baudrate(self) -> None:
        """
        Test that _configure_tty_settings raises ValueError for an unsupported baudrate
        rather than silently falling back to 9600:
        """
        # Move off 9600 so that a silent fallback would change the port speeds:
        self.serial.set_baudrate(19200)

        before = termios.tcgetattr(self.slave_file_descriptor)

        self.serial._baudrate = cast(BaudrateType, 12345)

        with self.assertRaises(ValueError):
            self.serial._configure_tty_settings(self.serial._get_termios_attributes())

        after = termios.tcgetattr(self.slave_file_descriptor)
        # The input and output speeds of the port must not have been reconfigured:
        self.assertEqual(after[4:6], before[4:6])

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

    async def test_open_sets_modem_lines(self) -> None:
        """
        Test that open sets DTR and sets RTS only when rtscts is enabled:
        """
        for rtscts in (False, True):
            with self.subTest(rtscts=rtscts):
                serial = SerialCommonInterface(
                    port=self.slave_device_name,
                    baudrate=9600,
                    params={
                        "bytesize": 8,
                        "parity": "N",
                        "stopbits": 1,
                        "timeout": 0.1,
                        "xonxoff": False,
                        "rtscts": rtscts,
                    },
                )

                with unittest.mock.patch.object(
                    SerialCommonInterface, "_set_modem_lines", autospec=True
                ) as set_modem_lines:
                    await serial.open()

                set_modem_lines.assert_called_once_with(serial, dtr=True, rts=rtscts)
                await serial.close()

    async def test_set_modem_lines_sets_dtr_bit(self) -> None:
        """
        Test that _set_modem_lines sets the DTR bit via TIOCMSET:
        """
        # Used to capture the modem bits written by TIOCMSET:
        written: list[int] = []

        def fake_ioctl(fd: int, request: int, buffer: bytes) -> bytes:
            if request == termios.TIOCMGET:
                return struct.pack("I", 0)
            if request == termios.TIOCMSET:
                written.append(struct.unpack("I", buffer)[0])
            return buffer

        with unittest.mock.patch("samps.asynchronous.ioctl", new=fake_ioctl):
            self.serial._set_modem_lines(dtr=True, rts=False)

        self.assertEqual(written, [termios.TIOCM_DTR])

    async def test_set_modem_lines_ignores_enotty(self) -> None:
        """
        Test that _set_modem_lines ignores ENOTTY from TIOCMGET:
        """
        with unittest.mock.patch(
            "samps.asynchronous.ioctl", side_effect=OSError(ENOTTY, "not a tty")
        ) as ioctl:
            self.serial._set_modem_lines(dtr=True, rts=False)

        ioctl.assert_called_once()
        self.assertEqual(ioctl.call_args.args[1], termios.TIOCMGET)

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
