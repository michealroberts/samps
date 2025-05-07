# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

from termios import (
    B0,
    B50,
    B75,
    B110,
    B134,
    B150,
    B200,
    B300,
    B600,
    B1200,
    B1800,
    B2400,
    B4800,
    B9600,
    B19200,
    B38400,
    B57600,
    B115200,
    B230400,
)
from typing import Dict, Literal, TypeAlias

# **************************************************************************************

"""
List of standard baud rate constants used in serial communication.

These constants are imported from the termios module and represent the speeds at which 
data can be transmitted over a serial connection.
"""
BAUDRATES: list[int] = [
    B0,
    B50,
    B75,
    B110,
    B134,
    B150,
    B200,
    B300,
    B600,
    B1200,
    B1800,
    B2400,
    B4800,
    B9600,
    B19200,
    B38400,
    B57600,
    B115200,
    B230400,
]

# **************************************************************************************

# A Literal type alias for valid numeric baud rate values:
BaudrateType: TypeAlias = Literal[
    0,
    50,
    75,
    110,
    134,
    150,
    200,
    300,
    600,
    1200,
    1800,
    2400,
    4800,
    9600,
    19200,
    38400,
    57600,
    115200,
    230400,
]

# **************************************************************************************

# Mapping from each valid baud rate to its termios constant:
BAUDRATE_LOOKUP_FLAGS: Dict[BaudrateType, int] = {
    0: B0,
    50: B50,
    75: B75,
    110: B110,
    134: B134,
    150: B150,
    200: B200,
    300: B300,
    600: B600,
    1200: B1200,
    1800: B1800,
    2400: B2400,
    4800: B4800,
    9600: B9600,
    19200: B19200,
    38400: B38400,
    57600: B57600,
    115200: B115200,
    230400: B230400,
}

# **************************************************************************************
