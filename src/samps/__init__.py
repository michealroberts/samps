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
    SerialInitialisationParameters,
)
from .errors import (
    SerialReadError,
    SerialTimeoutError,
    SerialWriteError,
)

# If the operating system is POSIX compliant, import the Serial class from the common module:
if name == "posix":
    from .common import SerialCommonInterface as Serial

# **************************************************************************************

__version__ = "0.3.0"

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
    "SerialInitialisationParameters",
    "SerialReadError",
    "SerialTimeoutError",
    "SerialWriteError",
]

# **************************************************************************************
