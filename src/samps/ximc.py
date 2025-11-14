# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

from struct import pack, unpack_from
from typing import Final

from .common import SerialCommonInterface
from .crc import get_cyclic_redundancy_checksum
from .errors import (
    SerialWriteError,
    XIMCCommandNotRecognisedError,
    XIMCInvalidCRCError,
    XIMCValueOutOfRangeError,
)

# **************************************************************************************

# First 4 bytes of a reply are the echoed command:
XIMC_ECHO_SIZE: Final[int] = 4

# **************************************************************************************

# CRC16 (little-endian) appended after payload
XIMC_CRC_SIZE: Final[int] = 2

# **************************************************************************************


class XIMCSerialInterface(SerialCommonInterface):
    def write(self, data: bytes) -> int:
        # Expect data = command(4) + payload; CRC covers payload only:
        if len(data) < XIMC_ECHO_SIZE:
            raise SerialWriteError("Data is too short to contain command")

        # Compute CRC16 (Modbus-style) and append it (little-endian):
        payload = data[XIMC_ECHO_SIZE:]

        checksum = get_cyclic_redundancy_checksum(payload, 16)

        return super().write(data + pack("<H", checksum))

    def read(self, size: int = 1) -> bytes:
        # Read enough bytes to ensure we get the expected number of non-zero bytes
        # after stripping leading zeros.
        expected_size = size + XIMC_CRC_SIZE

        # Buffer to hold incoming data
        buffer = b""

        # Read in chunks until we have enough non-zero bytes after stripping leading zeros.
        while True:
            buffer += super().read(
                expected_size - len(buffer) if expected_size - len(buffer) > 0 else 1
            )

            # Remove any leading zero bytes used for zero-byte resynchronisation:
            i = 0

            n = len(buffer)

            while i < n and buffer[i] == 0x00:
                i += 1

            frame = buffer[i:]

            # If we have enough non-zero bytes, break:
            if len(frame) >= expected_size:
                break

            # Otherwise, continue reading...

        if len(frame) < XIMC_CRC_SIZE:
            raise ValueError("Received data is too short to contain CRC")

        # Separate the data (command and any payload) and CRC:
        data = frame[:-XIMC_CRC_SIZE]

        crc = unpack_from("<H", frame[-XIMC_CRC_SIZE:])[0]

        checksum = get_cyclic_redundancy_checksum(data[4:], 16)

        # Ensure that the expected checksum matches the received CRC:
        if crc != checksum:
            raise ValueError(
                f"CRC mismatch: expected {hex(checksum)}, got {hex(crc)}",
            )

        # Extract the echoed command and any payload from the data:
        command, payload = data[:XIMC_ECHO_SIZE], data[XIMC_ECHO_SIZE:]

        if command == b"errc":
            raise XIMCCommandNotRecognisedError(
                "Controller returned ERRC (command not recognised)",
            )

        if command == b"errd":
            raise XIMCInvalidCRCError(
                "Controller returned ERRD (invalid data CRC received by controller)",
            )

        if command == b"errv":
            raise XIMCValueOutOfRangeError(
                "Controller returned ERRV (value out of range)",
            )

        # Strip off echoed command at start:
        if len(data) < XIMC_ECHO_SIZE:
            raise ValueError(
                "Received data is too short to contain echoed command",
            )

        return payload

    def ask(self, data: bytes, eol: bytes = b"\n", maximum_bytes: int = -1) -> bytes:
        # Perform a write/read transaction, framing handled automatically:
        self.write(data)
        # EOL handling is ignored; XIMC uses fixed-size replies:
        data = self.read(maximum_bytes if maximum_bytes > 0 else 64)
        return data


# **************************************************************************************
