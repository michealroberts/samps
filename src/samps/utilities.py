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


def hex_to_int(value: Tuple[int, int, int]) -> int:
    """
    Convert a fixed-length big endian tuple of bytes to an integer (0..0xFFFFFF).

    Args:
        value: A tuple of three integers, each in [0, 255].

    Returns:
        Integer in [0, 16777215].

    Raises:
        TypeError: If value is not a 3-tuple of ints.
        ValueError: If any byte is out of range.
    """
    # Validate the input type:
    if not (
        isinstance(value, tuple)
        and len(value) == 3
        and all(isinstance(b, int) for b in value)
    ):
        raise TypeError("value must be a tuple of three integers")

    # Validate each byte's range:
    for b in value:
        if not (0 <= b <= 0xFF):
            raise ValueError("each byte must be in the range 0..255")

    return (value[0] << 16) | (value[1] << 8) | value[2]


# **************************************************************************************


def no_op(*args, **kwargs) -> None:
    """
    A no-operation function that does nothing.

    This can be used as a placeholder or default callback.
    """
    pass


# **************************************************************************************
