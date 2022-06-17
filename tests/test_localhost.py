import time
import threading
import Pyro5.core
import Pyro5.client
import Pyro5.nameserver
from Pyro5 import config
import pytest

@pytest.mark.skip("has errors in the test logic that need to be fixed first")
class TestNameServerLocalhost:
    _run = True

    def _condition(self):
        return self._run

    @staticmethod
    def _get_ip_of_host():
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(('10.255.255.255', 1))
            ip_address = sock.getsockname()[0]
        finally:
            sock.close()
        return ip_address

    def setup_name_server(self, host, broadcast):
        config.POLLTIMEOUT = 0.1
        self.nsUri, self.nameserver, self.bcserver = Pyro5.nameserver.start_ns(host=host, enableBroadcast=broadcast)
        self.thread = threading.Thread(target=self.nameserver.requestLoop, args=[self._condition])
        self.thread.start()
        if self.bcserver is not None:
            self.bcthread = self.bcserver.runInThread()

    def teardown_method(self):
        self._run = False
        time.sleep(0.01)
        self.nameserver.shutdown()
        if self.bcserver is not None:
            self.bcserver.close()
        self.thread.join(0.1)

    @pytest.mark.timeout(2)
    @pytest.mark.parametrize(
        ("host", "port", "broadcast"),
        (
            ("", None, True),   # default config
            ("", None, False),
            ("localhost", None, True),
            ("localhost", None, False),
            ("localhost", 9090, True),
            ("localhost", 9090, False),
            ("127.0.0.1", None, True),
            ("127.0.0.1", None, False),
            ("127.0.0.1", 9090, True),
            ("127.0.0.1", 9090, False),
        )
    )
    @pytest.mark.parametrize(
        "start_ns_param_host",
        (
            "",
            None,
        )
    )
    def test_locate_ns_on_localhost(self, start_ns_param_host, host, port, broadcast):
        self.setup_name_server(start_ns_param_host, broadcast)
        if host:
            assert host in self.nsUri
        if broadcast:
            assert self.bcserver
        else:
            assert self.bcserver is None
        ns = Pyro5.core.locate_ns(host=host, port=port, broadcast=broadcast)  # lookup on localhost
        assert isinstance(ns, Pyro5.client.Proxy)
        ns._pyroRelease()

    def test_locate_ns_with_host_ip(self):
        self.setup_name_server(self._get_ip_of_host(), True)
        assert self.bcserver
        ns = Pyro5.core.locate_ns()  # broadcast lookup even if host ip
        assert isinstance(ns, Pyro5.client.Proxy)
        ns._pyroRelease()