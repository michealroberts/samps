# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

from .baudrate import BAUDRATE_LOOKUP_FLAGS, BAUDRATES, BaudrateType
from .common import SerialCommonInterface, SerialCommonInterfaceParameters
from .errors import (
    SerialReadError,
    SerialTimeoutError,
    SerialWriteError,
)

# **************************************************************************************

__version__ = "0.1.0"

# **************************************************************************************

__license__ = "MIT"

# **************************************************************************************

__all__: list[str] = [
    "__version__",
    "__license__",
    "BAUDRATE_LOOKUP_FLAGS",
    "BAUDRATES",
    "BaudrateType",
    "SerialCommonInterface",
    "SerialCommonInterfaceParameters",
    "SerialReadError",
    "SerialTimeoutError",
    "SerialWriteError",
]

# **************************************************************************************
