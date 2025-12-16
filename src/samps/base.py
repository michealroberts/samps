# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

from types import TracebackType
from typing import Optional, Protocol, Type, runtime_checkable

# **************************************************************************************


@runtime_checkable
class BaseInterface(Protocol):
    """
    Protocol defining the interface for all base transport classes.

    All implementations must provide all methods with identical signatures.

    Unsupported operations should log a warning and return gracefully.
    """

    def open(self) -> None:
        """
        Open the connection to the device.

        Raises:
            Exception: If opening the connection fails.
        """
        ...

    def close(self) -> None:
        """
        Close the connection to the device if it is open.
        """
        ...

    def read(self, size: int = 1) -> bytes:
        """
        Read up to `size` bytes from the device.

        Args:
            size: Number of bytes to read (default: 1).

        Returns:
            A bytes object containing the data read.

        Raises:
            RuntimeError: If the connection is not open.
            Exception: On timeout or read errors.
        """
        ...

    def write(self, data: bytes) -> int:
        """
        Write all of `data` to the device.

        Args:
            data: Bytes to write.

        Returns:
            The total number of bytes successfully written.

        Raises:
            RuntimeError: If the connection is not open.
            Exception: On write failure.
        """
        ...

    def readline(
        self,
        eol: bytes = b"\n",
        maximum_bytes: int = -1,
    ) -> bytes:
        """
        Read up to and including the next `eol` byte sequence.

        Args:
            eol: End-of-line marker to read until (default: b'\\n').
            maximum_bytes: Maximum bytes to read (-1 for no limit).

        Returns:
            A bytes object containing the line read, including the EOL marker.

        Raises:
            RuntimeError: If the connection is not open.
            Exception: On timeout or read errors.
        """
        ...

    def ask(
        self,
        data: bytes,
        eol: bytes = b"\n",
        maximum_bytes: int = -1,
    ) -> bytes:
        """
        Write `data` to the device and read a response line ending with `eol`.

        Args:
            data: Bytes to write as the query.
            eol: End-of-line marker for the response (default: b'\n').
            maximum_bytes: Maximum bytes to read in response (-1 for no limit).

        Returns:
            The response bytes read from the device.

        Raises:
            RuntimeError: If the connection is not open.
            Exception: On write or read failure.
        """
        ...

    def flush(self) -> None:
        """
        Block until all written output has been transmitted to the device.

        Raises:
            RuntimeError: If the connection is not open.
        """
        ...

    def abort_in(self) -> None:
        """
        Discard any data waiting in the input buffer.

        Raises:
            RuntimeError: If the connection is not open.
        """
        ...

    def abort_out(self) -> None:
        """
        Discard any data waiting in the output buffer.

        Raises:
            RuntimeError: If the connection is not open.
        """
        ...

    def clear(self) -> None:
        """
        Clear the device by aborting all pending transfers and resetting I/O buffers.

        Raises:
            RuntimeError: If the connection is not open.
        """
        ...

    def is_open(self) -> bool:
        """
        Check whether the connection is currently open.

        Returns:
            True if open, False otherwise.
        """
        ...

    def is_closed(self) -> bool:
        """
        Check whether the connection is currently closed.

        Returns:
            True if closed, False otherwise.
        """
        ...

    def __enter__(self) -> "BaseInterface":
        """
        Synchronous context manager entry: opens the connection.

        Returns:
            The BaseInterface instance.
        """
        ...

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """
        Synchronous context manager exit: closes the connection.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception instance, if an exception was raised.
            exc_tb: The traceback, if an exception was raised.
        """
        ...

    async def __aenter__(self) -> "BaseInterface":
        """
        Asynchronous context manager entry: opens the connection.

        Returns:
            The BaseInterface instance.
        """
        ...

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """
        Asynchronous context manager exit: closes the connection.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception instance, if an exception was raised.
            exc_tb: The traceback, if an exception was raised.
        """
        ...

    def __repr__(self) -> str:
        """
        Return a string representation of the interface.

        Returns:
            A human-readable string describing the interface.
        """
        ...


# **************************************************************************************
