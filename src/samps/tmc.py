# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import os
from errno import EAGAIN, EINTR, EINVAL, ENOTTY, EWOULDBLOCK
from fcntl import ioctl
from select import select
from struct import pack
from termios import (
    CLOCAL,
    CREAD,
    CSIZE,
    ECHO,
    ECHOE,
    ECHOK,
    ECHONL,
    ICANON,
    ICRNL,
    IEXTEN,
    IGNBRK,
    IGNCR,
    INLCR,
    INPCK,
    ISIG,
    ISTRIP,
    OCRNL,
    ONLCR,
    OPOST,
    TCSANOW,
    VMIN,
    VTIME,
    tcsetattr,
)
from types import TracebackType
from typing import Optional, Type, TypedDict

from .errors import SerialReadError, SerialWriteError
from .handlers import ReadTimeoutHandler
from .tty import TTYAttributes, get_termios_attributes
from .utilities import no_op

# **************************************************************************************

# Default to a timeout of 2.0 seconds for USB TMC communication, this can be
# overridden in the USBTMCCommonInterfaceParameters:
DEFAULT_TIMEOUT = 2.0

# **************************************************************************************

USBTMC_IOCTL_CLEAR = 0x40045B04
USBTMC_IOCTL_ABORT_BULK_OUT = 0x40045B03
USBTMC_IOCTL_ABORT_BULK_IN = 0x40045B02

USBTMC_IOCTL_GET_TIMEOUT = 0x80045B09
USBTMC_IOCTL_SET_TIMEOUT = 0x40045B0A

# **************************************************************************************


class USBTMCCommonInterfaceParameters(TypedDict):
    """
    A representation of the parameters for a USBTMC common interface.
    """

    # The timeout for I/O operations (in seconds):
    timeout: Optional[float]


# **************************************************************************************

default_usbtmc_parameters: USBTMCCommonInterfaceParameters = (
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

    # The default timeout for the USBTMC connection is set to 2.0 seconds, as defined by
    # DEFAULT_TIMEOUT (blocking mode, in seconds):
    _timeout: float = DEFAULT_TIMEOUT

    # The default file descriptor for the USBTMC connection is set to None:
    _fd: Optional[int] = None

    # Whether the USBTMC port is open or not:
    _is_open: bool = False

    def __init__(
        self,
        port: str,
        params: USBTMCCommonInterfaceParameters = default_usbtmc_parameters,
    ) -> None:
        self._port = port

        timeout = params.get("timeout", None)

        # Ensure that the timeout is greater than or equal to 0:
        if timeout is not None and timeout < 0:
            raise ValueError("Timeout must be greater than or equal to 0")

        # Initialize the timeout handler with the provided timeout value:
        self._timeout = DEFAULT_TIMEOUT if timeout is None else timeout

        # Set the timeout directly on the USB TMC device:
        self.set_timeout(timeout=self._timeout)

    def _get_termios_attributes(self) -> TTYAttributes:
        """
        Retrieve the current TTY attributes for the open serial port.

        Returns:
            A TTYAttributes dict representing current termios settings.

        Raises:
            RuntimeError: If the file descriptor is not available.
        """
        if not self._fd:
            raise RuntimeError("File descriptor is not available.")

        # Only configure TTY settings if the file descriptor is a TTY:
        if not os.isatty(self._fd):
            raise RuntimeError("File descriptor is not a TTY device.")

        # Get the current TTY attributes for the file descriptor:
        return get_termios_attributes(self._fd)

    def _configure_tty_settings(self, attributes: TTYAttributes) -> None:
        """
        Apply configured TTY attributes to the serial port.

        Args:
            attributes: The TTYAttributes dict to set on the port.

        Raises:
            RuntimeError: If the file descriptor is not available.
            ValueError: If bytesize, stopbits, or parity parameters are invalid.
        """
        if not self._fd:
            raise RuntimeError("File descriptor is not available.")

        # Only configure TTY settings if the file descriptor is a TTY:
        if not os.isatty(self._fd):
            return

        attributes = self._get_termios_attributes()

        # Enable local mode and receiver:
        attributes["cflag"] |= CLOCAL | CREAD

        # Disable canonical mode, echo, signals and extensions:
        attributes["lflag"] &= ~(ICANON | ECHO | ECHOE | ECHOK | ECHONL | ISIG | IEXTEN)

        # Disable all output processing:
        attributes["oflag"] &= ~(OPOST | ONLCR | OCRNL)

        # Disable input transformations and parity checking:
        attributes["iflag"] &= ~(INLCR | IGNCR | ICRNL | IGNBRK | INPCK | ISTRIP)

        attributes["cflag"] &= ~CSIZE

        # Configure VMIN/VTIME for read timeouts:
        attributes["control_chars"][VMIN] = 1 if self._timeout is None else 0
        attributes["control_chars"][VTIME] = (
            0 if self._timeout is None else int(self._timeout * 10)
        )

        # Construct the TTY attributes list in the format expected by tcsetattr:
        tty_attributes: list[int | list[int]] = [
            attributes["iflag"],
            attributes["oflag"],
            attributes["cflag"],
            attributes["lflag"],
            attributes["ispeed"],
            attributes["ospeed"],
            attributes["control_chars"],
        ]

        # Apply modified attributes to the file descriptor immediately:
        tcsetattr(
            self._fd,
            TCSANOW,
            tty_attributes,
        )

    def open(self) -> None:
        """
        Open the USBTMC device for communication (non-blocking file descriptor).

        Raises:
            SerialReadError: If opening the device fails.
        """
        # Specify the flags for opening the USBTMC device, e.g., in read/write mode,
        # and in non-blocking mode:
        flags = os.O_RDWR | os.O_NONBLOCK

        try:
            # Attempt to open the USBTMC device with the specified flags:
            fd = os.open(self._port, flags)
        except OSError as e:
            raise SerialReadError(f"Failed to open port {self._port}: {e}") from e

        self._fd = fd

        # Get the raw TTY termios attributes for the file descriptor:
        attributes = self._get_termios_attributes()

        # Configure the TTY settings using the provided attributes (if applicable):
        self._configure_tty_settings(attributes)

        # Finally, set the USBTMC device to open:
        self._is_open = True

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
        Read up to `size` bytes from the serial port, respecting the configured timeout.

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
                [self._fd], [], [], max(0.0, min(self._timeout, remaining or 0.0))
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
                raise SerialReadError(f"Reading from USBTMC device failed: {e}")

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

            # Wait for readability with the remaining time budget
            remaining = timer.remaining()

            r, _, _ = select(
                [self._fd], [], [], max(0.0, min(self._timeout, remaining or 0.0))
            )

            if not r:
                raise SerialReadError(
                    f"Read timeout after {self._timeout}s (no data ready)"
                )

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
                raise SerialReadError(f"Reading from serial port failed: {e}")

            # If the port was ready but returned no data, treat it as a disconnection.
            if not chunk:
                raise SerialReadError(
                    "The device reported readiness to read but returned no data."
                )

            # If the chunk read was successful, process it by checking if the end-of-line
            # marker is within this chunk
            if eol in chunk:
                # Find the index position of the marker and append up to and including it:
                index = chunk.index(eol) + len(eol)
                read.extend(chunk[:index])
                break

            # Otherwise, append the entire chunk
            read.extend(chunk)

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
        # Check if the file descriptor is a valid integer:
        if not self.is_open():
            raise RuntimeError(
                "Port must be configured and open before it can be used."
            )

        # This is needed for type narrowing the file descriptor:
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        # No-op for USBTMC (no termios drain):
        return no_op()

    def abort_in(self) -> None:
        """
        Abort any pending Bulk-IN transfer on the device.
        """
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        is_atty = os.isatty(self._fd)

        try:
            ioctl(self._fd, USBTMC_IOCTL_ABORT_BULK_IN) if not is_atty else no_op()
        except OSError as e:
            if e.errno in (ENOTTY, EINVAL):
                raise RuntimeError(
                    "USBTMC abort_bulk_in not supported by kernel driver"
                )

            raise SerialReadError(f"Abort Bulk-IN failed: {e}") from e

    def abort_out(self) -> None:
        """
        Abort any pending Bulk-OUT transfer on the device.
        """
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        is_atty = os.isatty(self._fd)

        try:
            ioctl(self._fd, USBTMC_IOCTL_ABORT_BULK_OUT) if not is_atty else no_op()
        except OSError as e:
            if e.errno in (ENOTTY, EINVAL):
                raise RuntimeError(
                    "USBTMC abort_bulk_out not supported by kernel driver"
                )
            raise SerialWriteError(f"Abort Bulk-OUT failed: {e}") from e

    def clear(self) -> None:
        """
        Clear the device (abort all pending transfers, reset the I/O pipes etc).
        """
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        is_atty = os.isatty(self._fd)

        try:
            ioctl(self._fd, USBTMC_IOCTL_CLEAR) if not is_atty else no_op()
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
        Check whether the USBTMC device is currently closed.

        Returns:
            True if closed, False otherwise.
        """
        return not self.is_open()

    @property
    def port(self) -> str:
        """
        Get the current USBTMC device path.

        Returns:
            The device path as a string.
        """
        return self._port

    def set_port(self, port: str) -> None:
        """
        Change the USBTMC device path.

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
            ioctl(self._fd, USBTMC_IOCTL_SET_TIMEOUT, pack("I", timeout_ms))
        except OSError as e:
            # Raise a friendlier error if the ioctl is not supported:
            if e.errno in (ENOTTY, EINVAL):
                raise RuntimeError(
                    "USBTMC set_timeout not supported by kernel driver"
                ) from e
            raise

        return

    def __enter__(self) -> "USBTMCCommonInterface":
        """
        Context manager entry: opens the USBTMC device.

        Returns:
            The USBTMCCommonInterface instance.
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
