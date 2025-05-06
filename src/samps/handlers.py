# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************


from time import monotonic
from typing import Optional

# **************************************************************************************


class ReadTimeoutHandler:
    """
    A handler for managing read timeouts in serial communication.

    Tracks a timeout period in milliseconds, provides methods to check
    whether the timeout has expired, retrieve the remaining time,
    start or reset the timer, and a repr string.
    """

    def __init__(self, timeout: Optional[float]) -> None:
        """
        Initialize with a timeout value in milliseconds.

        Args:
            timeout: timeout duration in milliseconds, or None to disable.
        """
        self._timeout = timeout

    def start(self) -> None:
        """
        Restart the timeout countdown from the current moment.
        """
        self._start = monotonic()

    def has_expired(self) -> bool:
        """
        Return True if the elapsed time since start() has reached
        or exceeded the timeout value.
        """
        # If no timeout is set, return None:
        if self._timeout is None:
            return False

        # If the timer hasn't started, we can't calculate remaining time:
        if self._start is None:
            raise RuntimeError("Timeout not started. Call start() first.")

        return ((monotonic() - self._start) * 1000) >= self._timeout

    def remaining(self) -> Optional[float]:
        """
        Return the number of milliseconds left before expiration,
        never negative.

        Returns:
            The remaining time in milliseconds, or None if timeouts are disabled.
        """
        # If no timeout is set, return None:
        if self._timeout is None:
            return None

        # If the timer hasn't started, we can't calculate remaining time:
        if self._start is None:
            raise RuntimeError("Timeout not started. Call start() first.")

        remaining = self._timeout - (monotonic() - self._start) * 1000
        return remaining if remaining > 0 else 0.0

    def reset(self) -> None:
        """
        Alias for start(): restart the timeout countdown.
        """
        self.start()

    def __repr__(self) -> str:
        # If the timeout is None, we can't calculate remaining time:
        if self._timeout is None:
            return "<ReadTimeoutHandler timeout=None>"

        # If the timer hasn't started, we can't calculate remaining time:
        if self._start is None:
            return f"<ReadTimeoutHandler timeout={self._timeout:.0f}ms, remaining=NotStarted>"

        # Otherwise, return back the remaining time:
        return (
            f"<ReadTimeoutHandler timeout={self._timeout:.0f}ms, "
            f"remaining={self.remaining():.0f}ms>"
        )


# **************************************************************************************
