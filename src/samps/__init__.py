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
from .baudrate import BAUDRATE_LOOKUP_FLAGS, BAUDRATES, BaudrateType
from .common import (
    SerialCommonInterface,
    SerialCommonInterfaceParameters,
)
from .crc import get_cyclic_redundancy_checksum
from .errors import (
    SerialReadError,
    SerialTimeoutError,
    SerialWriteError,
)
from .utilities import hex_to_int, int_to_hex

# If the operating system is POSIX compliant, import the Serial class from the common module:
if name == "posix":
    from .common import SerialCommonInterface as Serial

# **************************************************************************************

__version__ = "0.8.0"

# **************************************************************************************

__license__ = "MIT"

# **************************************************************************************

__all__: list[str] = [
    "__version__",
    "__license__",
    "BAUDRATE_LOOKUP_FLAGS",
    "BAUDRATES",
    "BaudrateType",
    "Serial",
    "SerialAsyncCommonInterface",
    "SerialCommonInterface",
    "SerialCommonInterfaceParameters",
    "SerialReadError",
    "SerialTimeoutError",
    "SerialWriteError",
    "get_cyclic_redundancy_checksum",
    "hex_to_int",
    "int_to_hex",
]

# **************************************************************************************
