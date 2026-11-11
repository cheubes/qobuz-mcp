import os
from collections.abc import Iterator

import keyring
import pytest

from tests.memory_keyring import MemoryKeyring

# Inherited by subprocesses started from tests, such as the stdio server.
os.environ["PYTHON_KEYRING_BACKEND"] = "tests.memory_keyring.MemoryKeyring"


@pytest.fixture(autouse=True)
def memory_keyring() -> Iterator[MemoryKeyring]:
    backend = MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
