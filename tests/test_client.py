import copy
import pytest
import Pyro5.client
import Pyro5.errors


class TestClient:
    def test_proxy(self):
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.client.Proxy("burp")
        p1 = Pyro5.client.Proxy("PYRO:obj@host:5555")
        p1._pyroHandshake = "milkshake"
        p1._pyroTimeout = 42
        p1._pyroSeq = 100
        p1._pyroMaxRetries = 99
        p1._pyroRawWireResponse = True
        p2 = copy.copy(p1)
        assert p1 == p2
        assert p1 is not p2
        assert p1._pyroUri == p2._pyroUri
        assert p1._pyroHandshake == p2._pyroHandshake
        assert p1._pyroTimeout == p2._pyroTimeout
        assert p1._pyroMaxRetries == p2._pyroMaxRetries
        assert p1._pyroRawWireResponse == p2._pyroRawWireResponse
        assert p2._pyroSeq == 0



