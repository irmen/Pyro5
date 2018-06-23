import pytest
from Pyro5.compatibility import Pyro4


def test_compat_layer():
    from Pyro4 import naming
    with pytest.raises(NotImplementedError):
        naming.NameServer()
    from Pyro4 import socketutil
    assert socketutil.getIpVersion("127.0.0.1") == 4
    from Pyro4 import util
    try:
        _ = 1//0
    except ZeroDivisionError:
        tb = util.getPyroTraceback()
        assert len(tb) == 3
        assert "Traceback" in tb[0]
        assert "zero" in tb[2]
    Pyro4.URI("PYRO:test@localhost:5555")
    p = Pyro4.Proxy("PYRO:test@localhost:5555")
    Pyro4.BatchProxy(p)
    Pyro4.Daemon()
    with pytest.raises(NotImplementedError):
        _ = p._pyroHmacKey
    with pytest.raises(NotImplementedError):
        p._pyroHmacKey = b"fail"

