# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************


class BaseProtocolReadError(Exception):
    """
    Exception class for base protocol read errors.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# **************************************************************************************


class BaseProtocolTimeoutError(Exception):
    """
    Exception class for base protocol timeout errors.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# **************************************************************************************


class BaseProtocolWriteError(Exception):
    """
    Exception class for base protocol write errors.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# **************************************************************************************


class SerialReadError(Exception):
    """
    Exception class for serial read errors.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# **************************************************************************************


class SerialTimeoutError(Exception):
    """
    Exception class for serial timeout errors.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# **************************************************************************************


class SerialWriteError(Exception):
    """
    Exception class for serial write errors.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# **************************************************************************************
