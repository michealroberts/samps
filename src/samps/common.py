# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import os
import termios
from errno import EAGAIN, EINTR, EWOULDBLOCK
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
    PARODD,
    TCSANOW,
    VMIN,
    VTIME,
    tcdrain,
    tcgetattr,
    tcsetattr,
)
from types import TracebackType
from typing import Literal, Optional, Type, TypedDict

from .baudrate import BAUDRATE_LOOKUP_FLAGS, BAUDRATES, BaudrateType
from .errors import SerialReadError, SerialWriteError
from .handlers import ReadTimeoutHandler

# **************************************************************************************


class TTYAttributes(TypedDict):
    """
    A representation of the attributes of a TTY device.
    """

    # Input flags controlling how incoming bytes are interpreted:
    iflag: int

    # Output flags controlling how bytes are transmitted:
    oflag: int

    # Control flags for baud rate, character size, parity, stop bits, etc.:
    cflag: int

    # Local flags for canonical mode, echo, signal handling, and extensions:
    lflag: int

    # Input baud rate constant (e.g. termios.B9600):
    ispeed: int

    # Output baud rate constant (e.g. termios.B9600):
    ospeed: int

    # Control-character array (VMIN, VTIME, and other special chars):
    control_chars: list[int]


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

    # The timeout for the serial connection:
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
            "timeout": None,
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

    # The default timeout for the serial connection is set to None (blocking mode):
    _timeout: float = 0.0

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
        self._port = port
        self._bytesize = params.get("bytesize", 8)
        self._parity = params.get("parity", "N")
        self._stopbits = params.get("stopbits", 1)

        timeout = params.get("timeout", None)

        # Ensure that the timeout is greater than or equal to 0:
        if timeout is not None and timeout < 0:
            raise ValueError("Timeout must be greater than or equal to 0")

        # Initialize the timeout handler with the provided timeout value:
        self._timeout = timeout or 0.0

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
        Get the current TTY attributes for the serial port.
        """
        if not self._fd:
            raise RuntimeError("File descriptor is not available.")

        # Get the current TTY attributes for the file descriptor:
        attributes = tcgetattr(self._fd)

        # Convert the attributes to a dictionary format:
        return TTYAttributes(
            {
                "iflag": attributes[0],
                "oflag": attributes[1],
                "cflag": attributes[2],
                "lflag": attributes[3],
                "ispeed": attributes[4],
                "ospeed": attributes[5],
                "control_chars": list(attributes[6]),
            }
        )

    def _configure_tty_settings(self, attributes: TTYAttributes) -> None:
        """
        Configure the serial port with the specified parameters.
        This method is a placeholder and should be implemented in subclasses.
        """
        if not self._fd:
            raise RuntimeError("File descriptor is not available.")

        # Enable local mode and receiver:
        attributes["cflag"] |= CLOCAL | CREAD

        # Disable canonical mode, echo, signals and extensions:
        attributes["lflag"] &= ~(ICANON | ECHO | ECHOE | ECHOK | ECHONL | ISIG | IEXTEN)

        # Disable all output processing:
        attributes["oflag"] &= ~(OPOST | ONLCR | OCRNL)

        # Disable input transformations and parity checking:
        attributes["iflag"] &= ~(INLCR | IGNCR | ICRNL | IGNBRK | INPCK | ISTRIP)

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
        """"""
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

        # Switch the file descriptor back to blocking mode so reads honor termios VMIN/VTIME settings:
        os.set_blocking(fd, True)

        # Finally, set the serial port to open:
        self._is_open = True

    def close(self) -> None:
        """"""
        if self._fd is None:
            return

        os.close(self._fd)
        self._fd = None
        self._is_open = False

    def read(self, size: int = 1) -> bytes:
        """ """
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

        timer = ReadTimeoutHandler(timeout=self._timeout or 0.0)

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

            # If the port was ready but returned no data, treat it as a disconnection.
            if not chunk:
                raise SerialReadError(
                    "The device reported readiness to read but returned no data."
                )

            # If the chunk read was successful, append it to the data:
            read.extend(chunk)

        # Finally, return the accumulated data:
        return bytes(read)

    def write(self, data: bytes) -> int:
        """
        Write all of `data` to the serial port, retrying on EINTR/EAGAIN/EWOULDBLOCK
        and raising SerialReadError on fatal errors or if zero bytes are written.
        Returns the total number of bytes written.
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

    def flush(self) -> None:
        # Check if the file descriptor is a valid integer:
        if not self.is_open():
            raise RuntimeError(
                "Port must be configured and open before it can be used."
            )

        # This is needed for type narrowing the file descriptor:
        if self._fd is None:
            raise RuntimeError("File descriptor is not available.")

        # Wait until all output written to file descriptor fd has been
        # transmitted and drain:
        tcdrain(self._fd)

    def is_open(self) -> bool:
        """
        Check if the serial port is open, e.g., the file descriptor is available.

        Returns:
            bool: True if the serial port is open, False otherwise.
        """
        return self._fd is not None and self._is_open

    def is_closed(self) -> bool:
        """
        Check if the serial port is closed, e.g., the file descriptor is not available.

        Returns:
            bool: True if the serial port is closed, False otherwise.
        """
        return not self.is_open()

    @property
    def port(self) -> str:
        return self._port

    def set_port(self, port: str) -> None:
        self._port = port

        # Get the raw TTY termios attributes for the file descriptor:
        attributes = self._get_termios_attributes()

        # Configure the TTY settings using the provided attributes:
        self._configure_tty_settings(attributes)

    @property
    def baudrate(self) -> int:
        return self._baudrate

    def set_baudrate(self, baudrate: BaudrateType) -> None:
        self._baudrate = baudrate

        # Get the raw TTY termios attributes for the file descriptor:
        attributes = self._get_termios_attributes()

        # Configure the TTY settings using the provided attributes:
        self._configure_tty_settings(attributes)

    @property
    def bytesize(self) -> int:
        return self._bytesize

    def set_bytesize(self, bytesize: Literal[8, 7, 6, 5] = 8) -> None:
        self._bytesize = bytesize

        # Get the raw TTY termios attributes for the file descriptor:
        attributes = self._get_termios_attributes()

        # Configure the TTY settings using the provided attributes:
        self._configure_tty_settings(attributes)

    @property
    def parity(self) -> str:
        return self._parity

    def set_parity(self, parity: str) -> None:
        self._parity = parity

        # Get the raw TTY termios attributes for the file descriptor:
        attributes = self._get_termios_attributes()

        # Configure the TTY settings using the provided attributes:
        self._configure_tty_settings(attributes)

    def __enter__(self) -> "SerialCommonInterface":
        """
        Enter the runtime context and open the Serial port.
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
        Exit the runtime context and close the Serial port.
        """
        self.close()

    def __repr__(self) -> str:
        """
        Return a string representation of the SerialCommonInterface object.
        """
        return f"SerialCommonInterface(port={self._port}, baudrate={self._baudrate})"


# **************************************************************************************
