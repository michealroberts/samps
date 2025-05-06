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
