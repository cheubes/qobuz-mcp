import keyring
import pytest
from keyring.errors import PasswordDeleteError

from tests.memory_keyring import MemoryKeyring


def test_unit_tests_use_the_memory_backend() -> None:
    assert isinstance(keyring.get_keyring(), MemoryKeyring)


def test_memory_backend_stores_and_deletes_passwords() -> None:
    keyring.set_password("service", "user", "secret")
    assert keyring.get_password("service", "user") == "secret"
    keyring.delete_password("service", "user")
    assert keyring.get_password("service", "user") is None
    with pytest.raises(PasswordDeleteError):
        keyring.delete_password("service", "user")
