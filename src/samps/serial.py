# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import os
import termios
from errno import EAGAIN, EINTR, ENOTTY, EWOULDBLOCK
from fcntl import ioctl
from os import isatty
from struct import pack, unpack
from termios import (
    B9600,
    CLOCAL,
    CREAD,
    CRTSCTS,
    CS5,
    CS6,
    CS7,
    CS8,
    CSIZE,
    CSTOPB,
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
    IXANY,
    IXOFF,
    IXON,
    OCRNL,
    ONLCR,
    OPOST,
    PARENB,
    PARMRK,
    PARODD,
    TCIFLUSH,
    TCIOFLUSH,
    TCOFLUSH,
    TCSANOW,
    TIOCM_DTR,
    TIOCM_RTS,
    TIOCMGET,
    TIOCMSET,
    VMIN,
    VTIME,
    tcdrain,
    tcflush,
    tcsetattr,
)
from types import TracebackType
from typing import Literal, Optional, Type, TypedDict

from .baudrate import BAUDRATE_LOOKUP_FLAGS, BAUDRATES, BaudrateType
from .errors import SerialReadError, SerialWriteError
from .handlers import ReadTimeoutHandler
from .tty import TTYAttributes, get_termios_attributes
from .utilities import no_op

# **************************************************************************************

# Default to a timeout of 2.0 seconds for serial communication, this can be
# overridden in the SerialCommonInterfaceParameters:
DEFAULT_TIMEOUT = 2.0

# **************************************************************************************


class SerialCommonInterfaceParameters(TypedDict):
    """
    A representation of the parameters for a serial common interface.
    """

    # The bytesize for the serial connection:
    bytesize: Literal[8, 7, 6, 5]

    # The parity for the serial connection:
    parity: Literal["N", "E", "O"]

    # The stopbits for the serial connection:
    stopbits: Literal[1, 2]

    # The timeout for the serial connection (in seconds):
    timeout: Optional[float]

    # XON/XOFF flow control:
    xonxoff: bool

    # RTS/CTS flow control:
    rtscts: bool


# **************************************************************************************

default_serial_parameters: SerialCommonInterfaceParameters = (
    SerialCommonInterfaceParameters(
        {
            "bytesize": 8,
            "parity": "N",
            "stopbits": 1,
            "timeout": DEFAULT_TIMEOUT,
            "xonxoff": False,
            "rtscts": False,
        }
    )
)

# **************************************************************************************


class SerialCommonInterface:
    """
    This class provides a common interface for serial communication.
    """

    # The default port for the serial connection is set to "/dev/ttyUSB0":
    _port: str = "/dev/ttyUSB0"

    # The default baudrate for the serial connection is set to 9600:
    _baudrate: BaudrateType = 9600

    # The default bytesize for the serial connection is set to 8 bits:
    _bytesize: Literal[8, 7, 6, 5] = 8

    # The default parity for the serial connection is set to "N" (no parity):
    _parity: str = "N"

    # The default stopbits for the serial connection is set to 1:
    _stopbits: int = 1

    # The default timeout for the serial connection is set to 2.0 seconds, as defined by
    # DEFAULT_TIMEOUT (blocking mode, in seconds):
    _timeout: float = DEFAULT_TIMEOUT

    # The default xonxoff flow control for the serial connection is set to False:
    _xonxoff: bool = False

    # The default rtscts flow control for the serial connection is set to False:
    _rtscts: bool = False

    # The default file descriptor for the serial connection is set to None:
    _fd: Optional[int] = None

    # Whether the serial port is open or not:
    _is_open: bool = False

    def __init__(
        self,
        port: str,
        baudrate: BaudrateType = 9600,
        params: SerialCommonInterfaceParameters = default_serial_parameters,
    ) -> None:
        """
        Initialize the serial interface.

        Args:
            port: The device path for the serial port (e.g., "/dev/ttyUSB0").
            baudrate: The baud rate for communication (must be in BAUDRATES).
            params: A dict of serial parameters including bytesize, parity,
                    stopbits, timeout, xonxoff, and rtscts.

        Raises:
            ValueError: If timeout is negative or baudrate is invalid.
        """
        self._port = port
        self._bytesize = params.get("bytesize", 8)
        self._parity = params.get("parity", "N")
        self._stopbits = params.get("stopbits", 1)

        timeout = params.get("timeout", None)

        # Ensure that the timeout is greater than or equal to 0:
        if timeout is not None and timeout < 0:
            raise ValueError("Timeout must be greater than or equal to 0")

        # Initialize the timeout handler with the provided timeout value:
        self._timeout = DEFAULT_TIMEOUT if timeout is None else timeout

        # Ensure that the baudrate provided is valid:
        if baudrate not in BAUDRATE_LOOKUP_FLAGS.keys():
            # If the baudrate is not in the valid list, raise a ValueError:
            raise ValueError(
                f"Invalid baudrate: {baudrate}. Valid baudrates are: {BAUDRATES}"
            )

        self._baudrate = baudrate

        self._xonxoff = params.get("xonxoff", False)

        self._rtscts = params.get("rtscts", False)

    def _get_termios_attributes(self) -> TTYAttributes:
        """
        Retrieve the current TTY attributes for the open serial port.

        Returns:
            A TTYAttributes dict representing current termios settings.

        Raises:
            RuntimeError: If the file descriptor is not available.
        """
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

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
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        # Enable local mode and receiver:
        attributes["cflag"] |= CLOCAL | CREAD

        # Disable canonical mode, echo, signals and extensions:
        attributes["lflag"] &= ~(ICANON | ECHO | ECHOE | ECHOK | ECHONL | ISIG | IEXTEN)

        # Disable all output processing:
        attributes["oflag"] &= ~(OPOST | ONLCR | OCRNL)

        # Disable input transformations and parity checking:
        attributes["iflag"] &= ~(
            INLCR | IGNCR | ICRNL | IGNBRK | INPCK | ISTRIP | PARMRK
        )

        attributes["cflag"] &= ~CSIZE

        # Set character size:
        match self._bytesize:
            case 8:
                attributes["cflag"] |= CS8
            case 7:
                attributes["cflag"] |= CS7
            case 6:
                attributes["cflag"] |= CS6
            case 5:
                attributes["cflag"] |= CS5
            case _:
                raise ValueError(f"Invalid bytesize: {self._bytesize!r}")

        # Set stop bits:
        match self._stopbits:
            case 1:
                attributes["cflag"] &= ~CSTOPB
            case 2:
                attributes["cflag"] |= CSTOPB
            case _:
                raise ValueError(f"Invalid stopbits: {self._stopbits!r}")

        # Set parity bits:
        match self._parity:
            case "N":
                attributes["cflag"] &= ~(PARENB | PARODD)
            case "E":
                attributes["cflag"] |= PARENB
                attributes["cflag"] &= ~PARODD
            case "O":
                attributes["cflag"] |= PARENB | PARODD
            case _:
                raise ValueError(f"Invalid parity: {self._parity!r}")

        # Set software flow control:
        if self._xonxoff:
            attributes["iflag"] |= IXON | IXOFF
        else:
            attributes["iflag"] &= ~(IXON | IXOFF | IXANY)

        # Set hardware RTS/CTS flow control if supported:
        if hasattr(termios, "CRTSCTS"):
            if self._rtscts:
                attributes["cflag"] |= CRTSCTS
            else:
                attributes["cflag"] &= ~CRTSCTS

        # Set baud rates from BAUDRATES map:
        try:
            baudrate = BAUDRATE_LOOKUP_FLAGS.get(self._baudrate, B9600)
        except KeyError:
            raise ValueError(f"Unsupported baudrate: {self._baudrate!r}")

        # Configure input and output baud rates:
        attributes["ispeed"] = baudrate
        attributes["ospeed"] = baudrate

        # Return immediately when VTIME expires, even if no bytes are available:
        attributes["control_chars"][VMIN] = 0

        # Configure an inter-byte timeout that relates to the prescribed timeout and
        # clamp to a maximum of 255:
        attributes["control_chars"][VTIME] = max(
            1, min(255, int(round(self._timeout * 10)))
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

    def _set_modem_lines(self, dtr: bool = True, rts: bool = False) -> None:
        """
        Apply DTR and RTS modem control lines.

        Args:
            dtr: Whether to set (True) or clear (False) the DTR line.
            rts: Whether to set (True) or clear (False) the RTS line.

        Raises:
            RuntimeError: If the file descriptor is not available.

        Note:
            This method silently returns if the device is not a TTY or does not
            support modem control ioctls (ENOTTY).
        """
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        if not isatty(self._fd):
            return

        # Pack an unsigned int buffer to hold the modem bits:
        buffer = pack("I", 0)

        # Get the current modem bits; ignore if device does not support this ioctl:
        try:
            buffer = ioctl(self._fd, TIOCMGET, buffer)
        except OSError as error:
            if error.errno == ENOTTY:
                # PTYs and some drivers do not support modem control; just skip.
                return
            raise

        # Unpack the bits from the buffer:
        (bits,) = unpack("I", buffer)

        # If DTR is requested, set or clear the bit:
        if dtr:
            bits |= TIOCM_DTR
        else:
            bits &= ~TIOCM_DTR

        # If RTS is requested, set or clear the bit:
        if rts:
            bits |= TIOCM_RTS
        else:
            bits &= ~TIOCM_RTS

        buffer = pack("I", bits)

        ioctl(self._fd, TIOCMSET, buffer)

    def open(self) -> None:
        """
        Open the serial port, configure termios settings, and enable blocking reads.

        Raises:
            SerialReadError: If opening the port fails.
        """
        # Specify the flags for opening the serial port, e.g., in read/write mode,
        # without controlling terminal, and in non-blocking mode:
        flags = os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK

        try:
            # Attempt to open the serial port with the specified flags:
            fd = os.open(self._port, flags)
        except OSError as e:
            raise SerialReadError(f"Failed to open port {self._port}: {e}") from e

        self._fd = fd

        # Get the raw TTY termios attributes for the file descriptor:
        attributes = self._get_termios_attributes()

        # Configure the TTY settings using the provided attributes:
        self._configure_tty_settings(attributes)

        # After configuring termios, set the modem control lines:
        self._set_modem_lines(dtr=True, rts=True if self._rtscts else False)

        # Switch the file descriptor back to blocking mode so reads honor termios
        # VMIN/VTIME settings:
        os.set_blocking(fd, True)

        # Finally, set the serial port to open:
        self._is_open = True

    def close(self) -> None:
        """
        Close the serial port if it is open.
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
                raise SerialReadError(f"Reading from serial port failed: {e}")

            # Keep waiting for more bytes and do NOT treat as a disconnect:
            if not chunk:
                continue

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

            # Keep waiting for more bytes and do NOT treat as a disconnect:
            if not chunk:
                continue

            # If the chunk read was successful, process it by checking if the end-of-line
            # marker is within this chunk
            if chunk.endswith(eol) or eol in chunk:
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
        Write all of `data` to the serial port, retrying on transient errors.

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
                    continue
                raise SerialWriteError(f"Writing to serial port failed: {e}") from e

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
        # Send the request bytes to the device:
        self.write(data)
        # Ensure all bytes have physically left the OS driver and been transmitted
        # to the device before we start waiting for a response:
        self.flush()
        # Perform the readline operation after flushing the data bytes:
        return self.readline(eol, maximum_bytes)

    def flush(self) -> None:
        """
        Block until all written output has been transmitted to the serial device.

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

        # Wait until all output written to file descriptor fd has been
        # transmitted and drained:
        tcdrain(self._fd)

    def clear_buffer(self) -> None:
        """
        Clear both input and output buffers of the serial port.

        Raises:
            RuntimeError: If the port is not open or the file descriptor is not
            available.
        """
        self.abort_in()
        self.abort_out()

    def clear_input_buffer(self) -> None:
        """
        Discard data in the input buffer (flush the input buffer).
        """
        self.abort_in()

    def clear_output_buffer(self) -> None:
        """
        Discard data in the output buffer (flush the output buffer).
        """
        self.abort_out()

    def abort_in(self) -> None:
        """
        Discard data in the input buffer (flush the input buffer).
        """
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        if not self.is_open():
            raise RuntimeError(
                "Port must be configured and open before it can be used."
            )

        # Only meaningful for TTYs; if not a TTY (very rare for “serial”), treat as no-op:
        try:
            tcflush(self._fd, TCIFLUSH) if os.isatty(self._fd) else no_op()
        except OSError:
            # Some exotic drivers may not support tcflush; ignore these errors:
            pass

    def abort_out(self) -> None:
        """
        Discard data in the output buffer (flush the output buffer).
        """
        if not self.is_open():
            raise RuntimeError(
                "Port must be configured and open before it can be used."
            )

        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        # Only meaningful for TTYs; if not a TTY (very rare for “serial”), treat as no-op:
        try:
            tcflush(self._fd, TCOFLUSH) if os.isatty(self._fd) else no_op()
        except OSError:
            # Some exotic drivers may not support tcflush; ignore these errors:
            pass

    def clear(self) -> None:
        """
        Clear the device (abort all pending transfers, reset the I/O pipes etc).
        """
        if not self.is_open():
            raise RuntimeError(
                "Port must be configured and open before it can be used."
            )

        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        try:
            tcflush(self._fd, TCIOFLUSH) if os.isatty(self._fd) else no_op()
        except OSError:
            # Some exotic drivers may not support tcflush; ignore these errors:
            pass

    def is_open(self) -> bool:
        """
        Check whether the serial port is currently open.

        Returns:
            True if open, False otherwise.
        """
        return self._fd is not None and self._is_open

    def is_closed(self) -> bool:
        """
        Check whether the serial port is currently closed.

        Returns:
            True if closed, False otherwise.
        """
        return not self.is_open()

    @property
    def port(self) -> str:
        """
        Get the current serial port device path.

        Returns:
            The device path as a string.
        """
        return self._port

    def set_port(self, port: str) -> None:
        """
        Change the serial device path and reconfigure termios settings.

        Args:
            port: New device path (e.g., "/dev/ttyUSB1").
        """
        self._port = port

        # Get the raw TTY termios attributes for the file descriptor:
        attributes = self._get_termios_attributes()

        # Configure the TTY settings using the provided attributes:
        self._configure_tty_settings(attributes)

    @property
    def baudrate(self) -> int:
        """
        Get the current baud rate setting.

        Returns:
            The baud rate as an integer.
        """
        return self._baudrate

    def set_baudrate(self, baudrate: BaudrateType) -> None:
        """
        Change the baud rate and reconfigure termios settings.

        Args:
            baudrate: New baud rate (must be in BAUDRATES).
        """
        self._baudrate = baudrate

        # Get the raw TTY termios attributes for the file descriptor:
        attributes = self._get_termios_attributes()

        # Configure the TTY settings using the provided attributes:
        self._configure_tty_settings(attributes)

    @property
    def bytesize(self) -> int:
        """
        Get the current byte size (number of data bits).

        Returns:
            An integer (5, 6, 7, or 8).
        """
        return self._bytesize

    def set_bytesize(self, bytesize: Literal[8, 7, 6, 5] = 8) -> None:
        """
        Change the data bit size and reconfigure termios settings.

        Args:
            bytesize: Number of data bits (5, 6, 7, or 8).
        """
        self._bytesize = bytesize

        # Get the raw TTY termios attributes for the file descriptor:
        attributes = self._get_termios_attributes()

        # Configure the TTY settings using the provided attributes:
        self._configure_tty_settings(attributes)

    @property
    def parity(self) -> str:
        """
        Get the current parity setting ('N', 'E', or 'O').

        Returns:
            A single-character string.
        """
        return self._parity

    def set_parity(self, parity: str) -> None:
        """
        Change the parity mode and reconfigure termios settings.

        Args:
            parity: Parity mode ('N' for none, 'E' for even, 'O' for odd).
        """
        self._parity = parity

        # Get the raw TTY termios attributes for the file descriptor:
        attributes = self._get_termios_attributes()

        # Configure the TTY settings using the provided attributes:
        self._configure_tty_settings(attributes)

    def __enter__(self) -> "SerialCommonInterface":
        """
        Context manager entry: opens the serial port.

        Returns:
            The SerialCommonInterface instance.
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
        Context manager exit: closes the serial port.
        """
        try:
            self.clear()
        finally:
            self.close()

    def __repr__(self) -> str:
        """
        Return a string representation of the interface.

        Returns:
            A string in the form: SerialCommonInterface(port=<port>, baudrate=<baudrate>).
        """
        return f"SerialCommonInterface(port={self._port}, baudrate={self._baudrate})"


# **************************************************************************************
