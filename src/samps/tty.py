# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

from termios import tcgetattr
from typing import TypedDict

# **************************************************************************************


class TTYAttributes(TypedDict):
    """
    A representation of the attributes of a TTY device.
    """

    # Input flags controlling how incoming bytes are interpreted:
    iflag: int

    # Output flags controlling how bytes are transmitted:
    oflag: int

    # Control flags for baud rate, character size, parity, stop bits, etc.:
    cflag: int

    # Local flags for canonical mode, echo, signal handling, and extensions:
    lflag: int

    # Input baud rate constant (e.g. termios.B9600):
    ispeed: int

    # Output baud rate constant (e.g. termios.B9600):
    ospeed: int

    # Control-character array (VMIN, VTIME, and other special chars):
    control_chars: list[int]


# **************************************************************************************


def get_termios_attributes(fd: int) -> TTYAttributes:
    """
    Retrieve the termios attributes for a given file descriptor

    Args:
        fd: The file descriptor of the TTY device.

    Returns:
        A TTYAttributes dictionary containing the termios settings.
    """
    # Get the current TTY attributes for the file descriptor:
    attributes = tcgetattr(fd)

    # Convert the attributes to a dictionary format:
    return TTYAttributes(
        {
            "iflag": attributes[0],
            "oflag": attributes[1],
            "cflag": attributes[2],
            "lflag": attributes[3],
            "ispeed": attributes[4],
            "ospeed": attributes[5],
            "control_chars": list(attributes[6]),
        }
    )


# **************************************************************************************
