# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

from typing import Optional, TypedDict

# **************************************************************************************


class Port(TypedDict):
    # The name of the device entry, e.g., 'ttyUSB0':
    name: str
    # The vendor ID of the device, if available:
    vid: Optional[int]
    # The product ID of the device, if available:
    pid: Optional[int]


# **************************************************************************************
