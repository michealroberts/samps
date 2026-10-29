# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import unittest
from types import TracebackType
from typing import Optional, Type

import samps
from samps.base import BaseAsyncInterface

# **************************************************************************************


class FakeAsyncInterface:
    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def read(self, size: int = 1) -> bytes:
        return b""

    async def write(self, data: bytes) -> int:
        return len(data)

    async def readline(
        self,
        eol: bytes = b"\n",
        maximum_bytes: int = -1,
    ) -> bytes:
        return b""

    async def ask(
        self,
        data: bytes,
        eol: bytes = b"\n",
        maximum_bytes: int = -1,
    ) -> bytes:
        return b""

    async def flush(self) -> None:
        return None

    async def abort_in(self) -> None:
        return None

    async def abort_out(self) -> None:
        return None

    async def clear(self) -> None:
        return None

    def is_open(self) -> bool:
        return False

    def is_closed(self) -> bool:
        return True

    async def __aenter__(self) -> "FakeAsyncInterface":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        return None

    def __repr__(self) -> str:
        return "FakeAsyncInterface()"


# **************************************************************************************


class FakeAsyncInterfaceWithoutAsk:
    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def read(self, size: int = 1) -> bytes:
        return b""

    async def write(self, data: bytes) -> int:
        return len(data)

    async def readline(
        self,
        eol: bytes = b"\n",
        maximum_bytes: int = -1,
    ) -> bytes:
        return b""

    async def flush(self) -> None:
        return None

    async def abort_in(self) -> None:
        return None

    async def abort_out(self) -> None:
        return None

    async def clear(self) -> None:
        return None

    def is_open(self) -> bool:
        return False

    def is_closed(self) -> bool:
        return True

    async def __aenter__(self) -> "FakeAsyncInterfaceWithoutAsk":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        return None

    def __repr__(self) -> str:
        return "FakeAsyncInterfaceWithoutAsk()"


# **************************************************************************************


class ExplicitAsyncInterface(FakeAsyncInterface, BaseAsyncInterface):
    pass


# **************************************************************************************


class TestBaseAsyncInterface(unittest.TestCase):
    def test_fake_is_instance_of_base_async_interface(self) -> None:
        # Assert that a class implementing every member satisfies the protocol:
        self.assertIsInstance(FakeAsyncInterface(), BaseAsyncInterface)

    def test_fake_without_ask_is_not_instance_of_base_async_interface(self) -> None:
        # Assert that a class missing the ask member does not satisfy the protocol:
        self.assertNotIsInstance(FakeAsyncInterfaceWithoutAsk(), BaseAsyncInterface)

    def test_explicit_subclass_can_be_instantiated(self) -> None:
        # Assert that an explicit subclass implementing every member is not abstract:
        interface = ExplicitAsyncInterface()
        self.assertIsInstance(interface, BaseAsyncInterface)
        self.assertIn(BaseAsyncInterface, ExplicitAsyncInterface.__mro__)

    def test_base_async_interface_is_exported(self) -> None:
        # Assert that BaseAsyncInterface is importable from the samps package:
        self.assertIs(samps.BaseAsyncInterface, BaseAsyncInterface)
        self.assertIn("BaseAsyncInterface", samps.__all__)


# **************************************************************************************

if __name__ == "__main__":
    unittest.main()

# **************************************************************************************
