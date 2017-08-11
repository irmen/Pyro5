import pytest
import Pyro5.core
import Pyro5.errors


class TestCore:
    def test_uri(self):
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("burp")
        Pyro5.core.URI("PYRO:obj@host:5555")
