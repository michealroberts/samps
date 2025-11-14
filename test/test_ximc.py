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
from struct import pack
from typing import cast

from samps import (
    BAUDRATES,
    BaudrateType,
    SerialCommonInterfaceParameters,
    SerialReadError,
    SerialWriteError,
    XIMCSerialInterface,
    get_cyclic_redundancy_checksum,
)

# **************************************************************************************


class TestXIMCSerialInterface(unittest.TestCase):
    """
    Unit tests for XIMCSerialInterface using a pseudo-TTY device:
    """

    master_file_descriptor: int
    slave_file_descriptor: int
    slave_device_name: str
    serial: XIMCSerialInterface

    def setUp(self) -> None:
        """
        Create a pseudo-TTY pair and open the serial interface on the slave end:
        """
        self.master_file_descriptor, self.slave_file_descriptor = os.openpty()
        self.slave_device_name = os.ttyname(self.slave_file_descriptor)

        params = SerialCommonInterfaceParameters(
            {
                "bytesize": 8,
                "parity": "N",
                "stopbits": 2,
                "timeout": 0.4,
                "xonxoff": False,
                "rtscts": False,
            }
        )

        self.serial = XIMCSerialInterface(
            port=self.slave_device_name,
            baudrate=115200,
            params=params,
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
        with XIMCSerialInterface(
            port=self.slave_device_name,
            baudrate=115200,
            params={
                "bytesize": 8,
                "parity": "N",
                "stopbits": 2,
                "timeout": 0.4,
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
        self.assertIn("115200", representation)

    def test_write_and_read_through_pty(self) -> None:
        """
        Test writing to the slave is readable from the master and vice versa:
        """
        data = b"hello-world"
        number_written = self.serial.write(data)
        self.assertEqual(number_written, len(data) + 2)

        received = os.read(self.master_file_descriptor, len(data) + 2)
        self.assertEqual(received[:-2], data)

        payload = data[4:]
        self.assertEqual(
            int.from_bytes(received[-2:], "little"),
            get_cyclic_redundancy_checksum(payload, 16),
        )

        echo = data[:4]
        reply_payload = payload
        reply_crc = get_cyclic_redundancy_checksum(reply_payload, 16)
        os.write(
            self.master_file_descriptor,
            echo
            + reply_payload
            + reply_crc.to_bytes(
                2,
                "little",
            ),
        )

        read_back = self.serial.read(len(echo) + len(reply_payload))
        self.assertEqual(read_back, reply_payload)

    def test_ask_through_pty(self) -> None:
        """
        Test the ask method for write followed by read:
        """
        query = b"hello-world\n"
        reply = b"echo: hello-world\n"

        echo = reply[:4]
        reply_payload = reply[4:]
        reply_crc = get_cyclic_redundancy_checksum(reply_payload, 16)
        os.write(
            self.master_file_descriptor,
            echo
            + reply_payload
            + reply_crc.to_bytes(
                2,
                "little",
            ),
        )

        response = self.serial.ask(query, maximum_bytes=len(echo) + len(reply_payload))
        self.assertEqual(response, reply_payload)

        written_back = os.read(self.master_file_descriptor, len(query) + 2)
        self.assertEqual(written_back[:-2], query)
        written_payload = query[4:]
        self.assertEqual(
            int.from_bytes(
                written_back[-2:],
                "little",
            ),
            get_cyclic_redundancy_checksum(written_payload, 16),
        )

    def test_read_zero_length(self) -> None:
        """
        Test that reading zero bytes raises an error:
        """
        with self.assertRaises(SerialReadError):
            self.serial.read(0)

    def test_write_zero_length(self) -> None:
        """
        Test that writing zero bytes raises:
        """
        with self.assertRaises(SerialWriteError):
            self.serial.write(b"")

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
            self.assertEqual(number_written, len(data) + 2)

            received = b""
            target = len(data) + 2
            while len(received) < target:
                received += os.read(self.master_file_descriptor, target - len(received))

            self.assertEqual(received[:-2], data)
            payload = data[4:]
            self.assertEqual(
                int.from_bytes(received[-2:], "little"),
                get_cyclic_redundancy_checksum(payload, 16),
            )

    def test_read_timeout_raises(self) -> None:
        """
        Test that read raises a SerialReadError after the timeout expires:
        """
        short_serial = XIMCSerialInterface(
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
        serial2 = XIMCSerialInterface(
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

    def test_home_roundtrip(self) -> None:
        command = "home".encode("ascii")
        payload = b""

        number_written = self.serial.write(command + payload)
        self.assertEqual(number_written, len(command) + len(payload) + 2)

        written = os.read(self.master_file_descriptor, number_written)
        self.assertEqual(written[:-2], command + payload)
        self.assertEqual(
            int.from_bytes(written[-2:], "little"),
            get_cyclic_redundancy_checksum(payload, 16),
        )

        crc = get_cyclic_redundancy_checksum(payload, 16)
        os.write(
            self.master_file_descriptor, command + payload + crc.to_bytes(2, "little")
        )

        received = self.serial.read(len(command) + len(payload))
        self.assertEqual(received, payload)

    def test_gpos_roundtrip(self) -> None:
        command = "gpos".encode("ascii")
        payload = b""

        number_written = self.serial.write(command + payload)
        self.assertEqual(number_written, len(command) + 2)
        written = os.read(self.master_file_descriptor, number_written)

        self.assertEqual(written[:-2], command + payload)
        self.assertEqual(
            int.from_bytes(
                written[-2:],
                "little",
            ),
            get_cyclic_redundancy_checksum(payload, 16),
        )

        crc = get_cyclic_redundancy_checksum(payload, 16)
        os.write(
            self.master_file_descriptor,
            command
            + payload
            + crc.to_bytes(
                2,
                "little",
            ),
        )

        received = self.serial.read(len(command) + len(payload))
        self.assertEqual(received, payload)

    def test_movr_roundtrip(self) -> None:
        command = "movr".encode("ascii")
        # DeltaPosition=200 (int32 LE), uDPos=0 (uint16 LE), Reserved=0 (uint32 LE, twice):
        payload = pack("<iHII", 200, 0, 0, 0)

        number_written = self.serial.write(command + payload)
        self.assertEqual(number_written, len(command) + len(payload) + 2)
        written = os.read(self.master_file_descriptor, number_written)

        self.assertEqual(written[:-2], command + payload)
        self.assertEqual(
            int.from_bytes(written[-2:], "little"),
            get_cyclic_redundancy_checksum(payload, 16),
        )

        crc = get_cyclic_redundancy_checksum(payload, 16)
        os.write(
            self.master_file_descriptor, command + payload + crc.to_bytes(2, "little")
        )

        received = self.serial.read(len(command) + len(payload))
        self.assertEqual(received, payload)

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
