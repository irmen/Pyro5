import socket
import pytest
from Pyro5.compatibility import Pyro4


def test_compat_config():
    import Pyro4
    conf = Pyro4.config.asDict()
    assert conf["NS_PORT"] == 9090
    Pyro4.config.NS_PORT = 12345
    conf = Pyro4.config.asDict()
    assert conf["NS_PORT"] == 12345


def test_compat_layer():
    from Pyro4 import naming
    from Pyro4 import socketutil
    from Pyro4 import util
    try:
        _ = 1//0
    except ZeroDivisionError:
        tb = util.getPyroTraceback()
        assert len(tb) == 3
        assert "Traceback" in tb[0]
        assert "zero" in tb[2]
    assert 4 == socketutil.getIpVersion("127.0.0.1")
    assert 6 == socketutil.getIpVersion("::1")
    Pyro4.URI("PYRO:test@localhost:5555")
    p = Pyro4.Proxy("PYRO:test@localhost:5555")
    Pyro4.BatchProxy(p)
    Pyro4.Daemon()
    assert socketutil.getIpAddress("localhost", ipVersion=4).startswith("127.0")
    if socket.has_ipv6:
        try:
            assert ":" in socketutil.getIpAddress("localhost", ipVersion=6)
        except socket.error as x:
            if str(x) != "unable to determine IPV6 address":
                raise
    assert "127.0.0.1" == socketutil.getIpAddress("127.0.0.1")
    assert "::1" == socketutil.getIpAddress("::1")
    assert "127.0.0.1" == socketutil.getInterfaceAddress("127.0.0.1")
    with pytest.raises(NotImplementedError):
        naming.NameServer()
    with pytest.raises(NotImplementedError):
        _ = p._pyroHmacKey
    with pytest.raises(NotImplementedError):
        p._pyroHmacKey = b"fail"

