# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import sys
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
    # Linux-only high-speed baud rates (typed for all platforms, but only present in
    # BAUDRATE_LOOKUP_FLAGS at runtime on Linux, so non-Linux platforms will reject them
    # with a ValueError when validated):
    460800,
    500000,
    576000,
    921600,
    1000000,
    1152000,
    1500000,
    2000000,
    2500000,
    3000000,
    3500000,
    4000000,
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

"""
Linux-only high-speed baud rates.

The POSIX standard only defines baud rate constants up to B38400, with B57600, B115200 
and B230400 being widely supported extensions. Linux additionally exposes high-speed 
constants (B460800 through B4000000) via termios, which are commonly used by USB-serial 
adapters (e.g., FTDI, CP210x, CH340) and embedded UARTs.

These constants are not available on all platforms (e.g., macOS), so we conditionally 
import them on Linux only, extending BAUDRATES and BAUDRATE_LOOKUP_FLAGS in place. Note 
that whilst the kernel accepts these rates, it is the responsibility of the caller to 
ensure that the underlying hardware actually supports the requested baud rate.
"""
if sys.platform == "linux":
    # Import the high-speed baud rate constants, which are only defined on Linux:
    from termios import (
        B460800,
        B500000,
        B576000,
        B921600,
        B1000000,
        B1152000,
        B1500000,
        B2000000,
        B2500000,
        B3000000,
        B3500000,
        B4000000,
    )

    # Append the high-speed termios constants to the list of standard baud rates:
    BAUDRATES.extend(
        [
            B460800,
            B500000,
            B576000,
            B921600,
            B1000000,
            B1152000,
            B1500000,
            B2000000,
            B2500000,
            B3000000,
            B3500000,
            B4000000,
        ]
    )

    # Map each numeric high-speed baud rate to its corresponding termios constant:
    BAUDRATE_LOOKUP_FLAGS.update(
        {
            460800: B460800,
            500000: B500000,
            576000: B576000,
            921600: B921600,
            1000000: B1000000,
            1152000: B1152000,
            1500000: B1500000,
            2000000: B2000000,
            2500000: B2500000,
            3000000: B3000000,
            3500000: B3500000,
            4000000: B4000000,
        }
    )

# **************************************************************************************
