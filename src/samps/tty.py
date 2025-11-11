# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

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
