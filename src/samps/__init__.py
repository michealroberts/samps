# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

from os import name

# If the operating system is Windows, raise an ImportError:
if name == "nt":
    raise ImportError(
        "The samps package is not supported on Windows yet. "
        "Please use a different operating system."
    )

# **************************************************************************************

from .asynchronous import SerialAsyncCommonInterface
from .base import BaseInterface
from .baudrate import BAUDRATE_LOOKUP_FLAGS, BAUDRATES, BaudrateType
from .crc import get_cyclic_redundancy_checksum
from .errors import (
    BaseProtocolReadError,
    SerialReadError,
    SerialTimeoutError,
    SerialWriteError,
)
from .serial import (
    SerialCommonInterface,
    SerialCommonInterfaceParameters,
)
from .serial import SerialCommonInterface as Serial
from .tmc import (
    USBTMCCommonInterface,
    USBTMCCommonInterfaceParameters,
)
from .tmc import USBTMCCommonInterface as USBTMC
from .utilities import hex_to_int, int_to_hex

# **************************************************************************************

__version__ = "0.11.0"

# **************************************************************************************

__license__ = "MIT"

# **************************************************************************************

__all__: list[str] = [
    "__version__",
    "__license__",
    "BAUDRATE_LOOKUP_FLAGS",
    "BAUDRATES",
    "BaudrateType",
    "BaseInterface",
    "BaseProtocolReadError",
    "Serial",
    "SerialAsyncCommonInterface",
    "SerialCommonInterface",
    "SerialCommonInterfaceParameters",
    "SerialReadError",
    "SerialTimeoutError",
    "SerialWriteError",
    "USBTMCCommonInterface",
    "USBTMCCommonInterfaceParameters",
    "USBTMC",
    "get_cyclic_redundancy_checksum",
    "hex_to_int",
    "int_to_hex",
]

# **************************************************************************************
