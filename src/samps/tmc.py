# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import os
from errno import EAGAIN, EINTR, EINVAL, ENOTTY, EWOULDBLOCK
from fcntl import ioctl
from select import select
from struct import pack
from types import TracebackType
from typing import Optional, Type, TypedDict

from .errors import SerialReadError, SerialWriteError
from .handlers import ReadTimeoutHandler
from .utilities import no_op

# **************************************************************************************

# Default to a timeout of 2.0 seconds for USB TMC communication, this can be
# overridden in the USBTMCCommonInterfaceParameters:
DEFAULT_TIMEOUT = 2.0

# **************************************************************************************

IOCTL_CLEAR = 0x00005B02

IOCTL_ABORT_BULK_OUT = 0x00005B03

IOCTL_ABORT_BULK_IN = 0x00005B04

IOCTL_GET_TIMEOUT = 0x80045B09

IOCTL_SET_TIMEOUT = 0x40045B0A

# **************************************************************************************


class USBTMCCommonInterfaceParameters(TypedDict):
    """
    A representation of the parameters for a USBTMC common interface.
    """

    # The timeout for I/O operations (in seconds):
    timeout: Optional[float]


# **************************************************************************************

default_tmc_parameters: USBTMCCommonInterfaceParameters = (
    USBTMCCommonInterfaceParameters(
        {
            "timeout": DEFAULT_TIMEOUT,
        }
    )
)

# **************************************************************************************


class USBTMCCommonInterface:
    """
    This class provides a common interface for tmc over USB communication.
    """

    # The default port for the USBTMC communication is set to "/dev/usbtmc0":
    _port: str = "/dev/usbtmc0"

    # DEFAULT_TIMEOUT (non-blocking mode with select, in seconds):
    _timeout: float = DEFAULT_TIMEOUT

    # The default file descriptor for the USBTMC connection is set to None:
    _fd: Optional[int] = None

    # Whether the USBTMC port is open or not:
    _is_open: bool = False

    def __init__(
        self,
        port: str,
        params: USBTMCCommonInterfaceParameters = default_tmc_parameters,
    ) -> None:
        self._port = port

        timeout = params.get("timeout", None)

        # Ensure that the timeout is greater than or equal to 0:
        if timeout is not None and timeout < 0:
            raise ValueError("Timeout must be greater than or equal to 0")

        # Initialize the timeout handler with the provided timeout value:
        self._timeout = DEFAULT_TIMEOUT if timeout is None else timeout

    def open(self) -> None:
        """
        Open the USBTMC device for communication (non-blocking file descriptor).

        Raises:
            SerialReadError: If opening the device fails.
        """
        # Specify the flags for opening the USBTMC device, e.g., in read/write mode:
        flags = os.O_RDWR

        try:
            # Attempt to open the USBTMC device with the specified flags:
            fd = os.open(self._port, flags)
        except OSError as e:
            raise SerialReadError(f"Failed to open port {self._port}: {e}") from e

        self._fd = fd

        # Finally, set the USBTMC device to open:
        self._is_open = True

        # Set the timeout directly on the USB TMC device:
        self.set_timeout(timeout=self._timeout)

    def close(self) -> None:
        """
        Close the USBTMC device if it is open.
        """
        if self._fd is None:
            return

        os.close(self._fd)
        self._fd = None
        self._is_open = False

    def read(self, size: int = 1) -> bytes:
        """
        Read up to `size` bytes from the USBTMC device, respecting the configured
        timeout.

        Args:
            size: Number of bytes to read (default: 1).

        Returns:
            A bytes object containing the data read.

        Raises:
            RuntimeError: If the port is not open.
            SerialReadError: On timeout or read errors.
        """
        # Check if the file descriptor is a valid integer:
        if not self.is_open():
            raise RuntimeError(
                "Port must be configured and open before it can be used."
            )

        # This is needed for type narrowing the file descriptor:
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        if size == 0:
            return b""

        # Initialize a bytearray to accumulate incoming data:
        read: bytearray = bytearray()

        # Convert timeout from seconds to milliseconds, as required by ReadTimeoutHandler:
        timer = ReadTimeoutHandler(timeout=self._timeout * 1000)

        timer.start()

        # Continue reading until we have collected the requested number of bytes
        # or until the overall timeout period has elapsed.
        while len(read) < size:
            # Check if the timeout has expired:
            if timer.has_expired():
                raise SerialReadError(
                    f"Read timeout after {self._timeout}s, got {len(read)}/{size} bytes"
                )

            # Wait for readability with the remaining time budget
            remaining = timer.remaining()

            r, _, _ = select(
                [self._fd],
                [],
                [],
                max(0.0, min(self._timeout, (remaining or 0.0) / 1000.0)),
            )

            if not r:
                raise SerialReadError(
                    f"Read timeout after {self._timeout}s (no data ready)"
                )

            try:
                chunk: bytes = os.read(self._fd, size - len(read))
            except OSError as e:
                # Retry on non-fatal errors and propagate others upwards:
                if e.errno in (
                    EAGAIN,
                    EWOULDBLOCK,
                    EINTR,
                ):
                    continue
                raise SerialReadError(f"Reading from USBTMC device failed: {e}") from e

            # If the port was ready but returned no data, treat it as a disconnection.
            if not chunk:
                raise SerialReadError(
                    "The device reported readiness to read but returned no data."
                )

            # If the chunk read was successful, append it to the data:
            read.extend(chunk)

        # Finally, return the accumulated data:
        return bytes(read)

    def readline(self, eol: bytes = b"\n", maximum_bytes: int = -1) -> bytes:
        """
        Read up to and including the next `eol` byte (default b'\n'),
        or until `maximum_bytes` bytes have been read (if > 0),
        honoring self._timeout for the entire line.
        """
        # Check if the file descriptor is a valid integer:
        if not self.is_open():
            raise RuntimeError(
                "Port must be configured and open before it can be used."
            )

        # This is needed for type narrowing the file descriptor:
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        # Initialize a bytearray to accumulate incoming data:
        read: bytearray = bytearray()

        # Convert timeout from seconds to milliseconds, as required by ReadTimeoutHandler:
        timer = ReadTimeoutHandler(timeout=self._timeout * 1000)

        timer.start()

        # Determine how many bytes to read in this chunk:
        chunk_size = 1024

        # Continue reading until we have collected the requested number of bytes
        # or until the overall timeout period has elapsed:
        while True:
            # Check if we have read enough bytes to satisfy max_bytes:
            if maximum_bytes > 0 and len(read) >= maximum_bytes:
                break

            # Check if the timeout has expired:
            if timer.has_expired():
                raise SerialReadError(
                    f"Read timeout after {self._timeout}s, got {len(read)} bytes"
                )

            # Wait for readability with the remaining time budget:
            remaining = timer.remaining()

            r, _, _ = select(
                [self._fd],
                [],
                [],
                max(0.0, min(self._timeout, (remaining or 0.0) / 1000.0)),
            )

            # If no file descriptors are ready, return partial data if any is available:
            if not r:
                if len(read) > 0:
                    return bytes(read)

                raise SerialReadError(
                    f"Read timeout after {self._timeout}s (no data ready)"
                )

            # Limit read size if maximum_bytes is used:
            if maximum_bytes > 0:
                chunk_size = min(chunk_size, maximum_bytes - len(read))

            try:
                chunk: bytes = os.read(self._fd, chunk_size)
            except OSError as e:
                # Retry on non-fatal errors and propagate others upwards:
                if e.errno in (
                    EAGAIN,
                    EWOULDBLOCK,
                    EINTR,
                ):
                    continue
                raise SerialReadError(f"Reading from USBTMC device failed: {e}")

            # If the port was ready but returned no data, return partial data if any:
            if not chunk:
                if len(read) > 0:
                    return bytes(read)
                raise SerialReadError(
                    "The device reported readiness to read but returned no data."
                )

            # Append the entire chunk before checking for end-of-line:
            read.extend(chunk)

            # Process the buffer by checking if the end-of-line marker is within it:
            if eol in read:
                index = read.index(eol) + len(eol)
                return bytes(read[:index])

        # Finally, return the accumulated data:
        return bytes(read)

    def write(self, data: bytes) -> int:
        """
        Write all of `data` to the USBTMC device, retrying on transient errors.

        Args:
            data: Bytes to write.

        Returns:
            The total number of bytes successfully written.

        Raises:
            RuntimeError: If the port is not open.
            SerialWriteError: On write failure.
        """
        if not self.is_open():
            raise RuntimeError(
                "Port must be configured and open before it can be used."
            )

        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        if len(data) == 0:
            return 0

        written = 0

        # Loop until all bytes are written
        while written < len(data):
            try:
                n = os.write(self._fd, data[written:])
            except OSError as e:
                # Retry on transient POSIX errors:
                if e.errno in (EAGAIN, EWOULDBLOCK, EINTR):
                    _, w, _ = select([], [self._fd], [], self._timeout)

                    if not w:
                        raise SerialWriteError(
                            f"Write timeout after {self._timeout}s (not writable)"
                        )
                    continue
                raise SerialWriteError(f"Writing to USBTMC device failed: {e}") from e

            # If write returns 0, something is wrong (e.g. port closed)
            if n == 0:
                raise SerialWriteError(
                    "The device reported readiness to write but wrote zero bytes."
                )

            written += n

        return written

    def ask(self, data: bytes, eol: bytes = b"\n", maximum_bytes: int = -1) -> bytes:
        """
        Ask the device by writing `data` and reading a response line ending with `eol`.

        Args:
            data: Bytes to write as the query.
            eol: End-of-line marker for the response (default: b'\n').
            maximum_bytes: Maximum bytes to read in response (-1 for no limit).

        Returns:
            The response bytes read from the device.
        """
        self.write(data)
        return self.readline(eol, maximum_bytes)

    def flush(self) -> None:
        """
        Block until all written output has been transmitted to the device.

        Raises:
            RuntimeError: If the port is not open.
        """
        # No-op for USBTMC (no termios drain):
        return no_op()

    def abort_in(self) -> None:
        """
        Abort any pending Bulk-IN transfer on the device.
        """
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        try:
            ioctl(self._fd, IOCTL_ABORT_BULK_IN)
        except OSError as e:
            if e.errno in (ENOTTY, EINVAL):
                raise RuntimeError("abort_bulk_in not supported by kernel driver")

            raise SerialReadError(f"Abort Bulk-IN failed: {e}") from e

    def abort_out(self) -> None:
        """
        Abort any pending Bulk-OUT transfer on the device.

        Raises:
            RuntimeError: If the port is not open.
            SerialWriteError: On abort failure.
        """
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        try:
            ioctl(self._fd, IOCTL_ABORT_BULK_OUT)
        except OSError as e:
            if e.errno in (ENOTTY, EINVAL):
                raise RuntimeError("abort_bulk_out not supported by kernel driver")
            raise SerialWriteError(f"Abort Bulk-OUT failed: {e}") from e

    def clear(self) -> None:
        """
        Clear the device (abort all pending transfers, reset the I/O pipes etc).

        Raises:
            RuntimeError: If the port is not open, or if the clear operation is not
            supported or fails.
        """
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        try:
            ioctl(self._fd, IOCTL_CLEAR)
        except OSError as e:
            if e.errno in (ENOTTY, EINVAL):
                raise RuntimeError("USBTMC clear not supported by kernel driver")
            raise RuntimeError(f"USBTMC clear failed: {e}") from e

    def is_open(self) -> bool:
        """
        Check whether the USBTMC device is currently open.

        Returns:
            True if open, False otherwise.
        """
        return self._fd is not None and self._is_open

    def is_closed(self) -> bool:
        """
        Check whether the TMC device is currently closed.

        Returns:
            True if closed, False otherwise.
        """
        return not self.is_open()

    @property
    def port(self) -> str:
        """
        Get the current TMC device path.

        Returns:
            The device path as a string.
        """
        return self._port

    def set_port(self, port: str) -> None:
        """
        Change the TMC device path.

        Args:
            port: New device path (e.g., "/dev/usbtmc1").
        """
        self._port = port

    @property
    def timeout(self) -> float:
        """
        Get the current I/O timeout in seconds.

        Returns:
            The timeout value in seconds.
        """
        return self._timeout

    def set_timeout(self, timeout: float) -> None:
        """
        Set the I/O timeout in seconds.

        Args:
            timeout: Desired timeout in seconds (>= 0.0).
        """
        if timeout < 0.0:
            raise ValueError("Timeout must be greater than or equal to 0.0")

        self._timeout = float(timeout)

        # If device is not open yet, defer the kernel call until open():
        if self._fd is None or not self.is_open():
            return

        timeout_ms = int(round(self._timeout * 1000.0))

        try:
            # Pack the 32-bit unsigned milliseconds value and issue the ioctl to
            # set timeout (milliseconds) in the driver:
            ioctl(self._fd, IOCTL_SET_TIMEOUT, pack("I", timeout_ms))
        except OSError as e:
            # Raise a friendlier error if the ioctl is not supported:
            if e.errno in (ENOTTY, EINVAL):
                return
            raise RuntimeError(f"Setting USBTMC timeout failed: {e}") from e

    def __enter__(self) -> "USBTMCCommonInterface":
        """
        Context manager entry: opens the USBTMC device.

        Returns:
            The TMCCommonInterface instance.
        """
        self.open()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """
        Context manager exit: closes the USBTMC device.
        """
        try:
            self.clear()
        except Exception:
            # Ignore lack of USBTMC support on PTYs or unsupported kernels:
            pass
        finally:
            self.close()

    def __repr__(self) -> str:
        """
        Return a string representation of the interface.

        Returns:
            A string in the form: USBTMCCommonInterface(port=<port>, timeout=<timeout>)
        """
        return f"USBTMCCommonInterface(port={self._port}, timeout={self._timeout})"


# **************************************************************************************
