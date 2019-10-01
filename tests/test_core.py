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

    def test_unix_uri(self):
        p = Pyro5.core.URI("PYRO:12345@./u:/tmp/sockname")
        assert p.object == "12345"
        assert p.sockname == "/tmp/sockname"
        p = Pyro5.core.URI("PYRO:12345@./u:../sockname")
        assert p.object == "12345"
        assert p.sockname == "../sockname"
        p = Pyro5.core.URI("PYRO:12345@./u:/path with spaces/sockname  ")
        assert p.object == "12345"
        assert p.sockname == "/path with spaces/sockname  "
