# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

from typing import Tuple

# **************************************************************************************


def int_to_hex(value: int) -> Tuple[int, int, int]:
    """
    Convert an integer (0..0xFFFFFF) to fixed-length big endian tuple of bytes.

    Args:
        value: Integer in [0, 16777215].

    Returns:
        A tuple of three integers, each in [0, 255].

    Raises:
        TypeError: If value is not an int (bools are rejected).
        ValueError: If value is out of range.
    """
    # Check that the value is an integer (bools are rejected):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("value must be an int (bool is not allowed)")

    # Check that the value is within the valid range of hexadecimal values:
    if not (0 <= value <= 0xFFFFFF):
        raise ValueError("value must be in the valid hex range 0..16777215 (0xFFFFFF)")

    return (
        # The first byte (most significant byte):
        (value >> 16) & 0xFF,  # MSB
        # The second byte:
        (value >> 8) & 0xFF,
        # The third byte (least significant byte):
        value & 0xFF,
    )


# **************************************************************************************
