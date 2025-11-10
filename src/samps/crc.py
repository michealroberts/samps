# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

from typing import Dict, Literal, TypedDict

# **************************************************************************************


class CRCSpecification(TypedDict):
    # The initial checksum register value:
    start: int
    # The polynomial to use for the CRC calculation:
    polynomial: int


# **************************************************************************************

CRC_SPEC_LOOKUP: Dict[Literal[8, 16, 32], CRCSpecification] = {
    # CRC-8-ATM:
    8: {
        "start": 0x00,
        "polynomial": 0x07,
    },
    # CRC-16-Modbus (reflected):
    16: {
        "start": 0xFFFF,
        "polynomial": 0xA001,
    },
    # CRC-32-IEEE (reflected):
    32: {
        "start": 0xFFFFFFFF,
        "polynomial": 0xEDB88320,
    },
}

# **************************************************************************************


def get_cyclic_redundancy_checksum(
    data: bytes,
    bits: Literal[8, 16, 32] = 16,
) -> int:
    """
    Compute the cyclic redundancy checksum (CRC) of the given data.

    Args:
        data: The input data as bytes.
        bits: The CRC bit size (8, 16, or 32). Default is 16.

    Returns:
        The computed CRC as an integer.
    """
    # Ensure only the supported bit sizes are used:
    if bits not in CRC_SPEC_LOOKUP:
        raise ValueError(f"Unsupported CRC bit size: {bits}")

    specification = CRC_SPEC_LOOKUP[bits]

    crc = specification["start"]

    polynomial = specification["polynomial"]

    for byte in data:
        # Combine the next byte with the current CRC register:
        crc ^= byte

        # Process each bit of the current byte:
        for _ in range(8):
            # CRC-8 (MSB-first): shift left and test bit 7 (0x80):
            if bits == 8:
                crc = (
                    ((crc << 1) ^ polynomial) & 0xFF
                    if crc & 0x80
                    else (crc << 1) & 0xFF
                )
            # CRC-16 and CRC-32 (reflected): shift right and test bit 0:
            else:
                crc = (crc >> 1) ^ polynomial if crc & 1 else crc >> 1

    mask = (1 << bits) - 1

    # CRC-32 final XOR value:
    if bits == 32:
        crc = (~crc) & 0xFFFFFFFF

    return crc & mask


# **************************************************************************************
