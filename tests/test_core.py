import copy
import pytest
import Pyro5.core
import Pyro5.errors


class TestCore:
    def test_uri(self):
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("burp")
        u1 = Pyro5.core.URI("PYRO:obj@host:5555")
        u2 = copy.copy(u1)
        assert str(u1) == str(u2)
        assert u1 == u2
        assert u1 is not u2

