"""
Tests for the name server (online/running).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import time
import pytest
import threading
import Pyro5.core
import Pyro5.client
import Pyro5.nameserver
import Pyro5.socketutil
from Pyro5.errors import CommunicationError, NamingError
from Pyro5 import config


class NSLoopThread(threading.Thread):
    def __init__(self, nameserver):
        super(NSLoopThread, self).__init__()
        self.setDaemon(True)
        self.nameserver = nameserver
        self.running = threading.Event()
        self.running.clear()

    def run(self):
        self.running.set()
        try:
            self.nameserver.requestLoop()
        except CommunicationError:
            pass  # ignore pyro communication errors


class TestBCSetup:
    def testBCstart(self):
        myIpAddress = Pyro5.socketutil.get_ip_address("", workaround127=True)
        nsUri, nameserver, bcserver = Pyro5.nameserver.start_ns(host=myIpAddress, port=0, bcport=0, enableBroadcast=False)
        assert bcserver is None
        nameserver.close()
        nsUri, nameserver, bcserver = Pyro5.nameserver.start_ns(host=myIpAddress, port=0, bcport=0, enableBroadcast=True)
        assert bcserver is not None
        assert bcserver.fileno() > 1
        assert bcserver.sock is not None
        nameserver.close()
        bcserver.close()


class TestNameServer:
    def setup_method(self):
        config.POLLTIMEOUT = 0.1
        myIpAddress = Pyro5.socketutil.get_ip_address("", workaround127=True)
        self.nsUri, self.nameserver, self.bcserver = Pyro5.nameserver.start_ns(host=myIpAddress, port=0, bcport=0)
        assert self.bcserver is not None
        self.bcserver.runInThread()
        self.daemonthread = NSLoopThread(self.nameserver)
        self.daemonthread.start()
        self.daemonthread.running.wait()
        time.sleep(0.05)
        self.old_bcPort = config.NS_BCPORT
        self.old_nsPort = config.NS_PORT
        self.old_nsHost = config.NS_HOST
        config.NS_PORT = self.nsUri.port
        config.NS_HOST = str(myIpAddress)
        config.NS_BCPORT = self.bcserver.getPort()

    def teardown_method(self):
        time.sleep(0.01)
        self.nameserver.shutdown()
        self.bcserver.close()
        self.daemonthread.join()
        config.NS_HOST = self.old_nsHost
        config.NS_PORT = self.old_nsPort
        config.NS_BCPORT = self.old_bcPort

    def testLookupUnixsockParsing(self):
        # this must not raise AttributeError, it did before because of a parse bug
        with pytest.raises(NamingError):
            Pyro5.core.locate_ns("./u:/tmp/Pyro5-naming.usock")

    def testLookupAndRegister(self):
        ns = Pyro5.core.locate_ns()  # broadcast lookup
        assert isinstance(ns, Pyro5.client.Proxy)
        ns._pyroRelease()
        ns = Pyro5.core.locate_ns(self.nsUri.host)  # normal lookup
        assert isinstance(ns, Pyro5.client.Proxy)
        uri = ns._pyroUri
        assert uri.protocol == "PYRO"
        assert uri.host == self.nsUri.host
        assert uri.port == config.NS_PORT
        ns._pyroRelease()
        ns = Pyro5.core.locate_ns(self.nsUri.host, config.NS_PORT)
        uri = ns._pyroUri
        assert uri.protocol == "PYRO"
        assert uri.host == self.nsUri.host
        assert uri.port == config.NS_PORT
        # check that we cannot register a stupid type
        with pytest.raises(TypeError):
            ns.register("unittest.object1", 5555)
        # we can register str or URI, lookup always returns URI
        ns.register("unittest.object2", "PYRO:55555@host.com:4444")
        assert ns.lookup("unittest.object2") == Pyro5.core.URI("PYRO:55555@host.com:4444")
        ns.register("unittest.object3", Pyro5.core.URI("PYRO:66666@host.com:4444"))
        assert ns.lookup("unittest.object3") == Pyro5.core.URI("PYRO:66666@host.com:4444")
        ns._pyroRelease()

    def testDaemonPyroObj(self):
        uri = self.nsUri
        uri.object = Pyro5.core.DAEMON_NAME
        with Pyro5.client.Proxy(uri) as daemonobj:
            daemonobj.ping()
            daemonobj.registered()
            with pytest.raises(AttributeError):
                daemonobj.shutdown()

    def testMulti(self):
        uristr = str(self.nsUri)
        p = Pyro5.client.Proxy(uristr)
        p._pyroBind()
        p._pyroRelease()
        uri = Pyro5.core.resolve(uristr)
        p = Pyro5.client.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri = Pyro5.core.resolve(uristr)
        p = Pyro5.client.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri = Pyro5.core.resolve(uristr)
        p = Pyro5.client.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri = Pyro5.core.resolve(uristr)
        p = Pyro5.client.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri = Pyro5.core.resolve(uristr)
        p = Pyro5.client.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        daemonUri = "PYRO:" + Pyro5.core.DAEMON_NAME + "@" + uri.location
        _ = Pyro5.core.resolve(daemonUri)
        _ = Pyro5.core.resolve(daemonUri)
        _ = Pyro5.core.resolve(daemonUri)
        _ = Pyro5.core.resolve(daemonUri)
        _ = Pyro5.core.resolve(daemonUri)
        _ = Pyro5.core.resolve(daemonUri)
        uri = Pyro5.core.resolve(daemonUri)
        pyronameUri = "PYRONAME:" + Pyro5.core.NAMESERVER_NAME + "@" + uri.location
        _ = Pyro5.core.resolve(pyronameUri)
        _ = Pyro5.core.resolve(pyronameUri)
        _ = Pyro5.core.resolve(pyronameUri)
        _ = Pyro5.core.resolve(pyronameUri)
        _ = Pyro5.core.resolve(pyronameUri)
        _ = Pyro5.core.resolve(pyronameUri)

    def testResolve(self):
        resolved1 = Pyro5.core.resolve(Pyro5.core.URI("PYRO:12345@host.com:4444"))
        resolved2 = Pyro5.core.resolve("PYRO:12345@host.com:4444")
        assert type(resolved1) is Pyro5.core.URI
        assert resolved1 == resolved2
        assert str(resolved1) == "PYRO:12345@host.com:4444"

        ns = Pyro5.core.locate_ns(self.nsUri.host, self.nsUri.port)
        host = "[" + self.nsUri.host + "]" if ":" in self.nsUri.host else self.nsUri.host
        uri = Pyro5.core.resolve("PYRONAME:" + Pyro5.core.NAMESERVER_NAME + "@" + host + ":" + str(self.nsUri.port))
        assert uri.protocol == "PYRO"
        assert uri.host == self.nsUri.host
        assert uri.object == Pyro5.core.NAMESERVER_NAME
        assert ns._pyroUri == uri
        ns._pyroRelease()

        # broadcast lookup
        with pytest.raises(NamingError):
            Pyro5.core.resolve("PYRONAME:unknown_object")
        uri = Pyro5.core.resolve("PYRONAME:" + Pyro5.core.NAMESERVER_NAME)
        assert isinstance(uri, Pyro5.core.URI)
        assert uri.protocol == "PYRO"

        # test some errors
        with pytest.raises(NamingError):
            Pyro5.core.resolve("PYRONAME:unknown_object@" + host)
        with pytest.raises(TypeError):
            Pyro5.core.resolve(999)

    def testRefuseDottedNames(self):
        with Pyro5.core.locate_ns(self.nsUri.host, self.nsUri.port) as ns:
            # the name server should never have dotted names enabled
            with pytest.raises(AttributeError):
                ns.namespace.keys
            assert ns._pyroConnection is not None
        assert ns._pyroConnection is None

    def testAutoClean(self):
        try:
            config.NS_AUTOCLEAN = 0.0
            config.COMMTIMEOUT = 0.5
            Pyro5.nameserver.AutoCleaner.max_unreachable_time = 1
            Pyro5.nameserver.AutoCleaner.loop_delay = 0.5
            Pyro5.nameserver.AutoCleaner.override_autoclean_min = True
            with Pyro5.nameserver.NameServerDaemon(port=0) as ns:
                assert ns.cleaner_thread is None
            config.NS_AUTOCLEAN = 0.2
            with Pyro5.nameserver.NameServerDaemon(port=0) as ns:
                assert ns.cleaner_thread is not None
                ns.nameserver.register("test", "PYRO:test@localhost:59999")
                assert ns.nameserver.count() == 2
                time.sleep(4)
                assert ns.nameserver.count() == 1
            assert ns.cleaner_thread is None
        finally:
            Pyro5.nameserver.AutoCleaner.override_autoclean_min = False
            Pyro5.nameserver.AutoCleaner.max_unreachable_time = 20
            Pyro5.nameserver.AutoCleaner.loop_delay = 2
            config.NS_AUTOCLEAN = 0.0
            config.COMMTIMEOUT = 0.0


class TestNameServer0000:
    def setup_method(self):
        config.POLLTIMEOUT = 0.1
        self.nsUri, self.nameserver, self.bcserver = Pyro5.nameserver.start_ns(host="", port=0, bcport=0)
        host_check = self.nsUri.host
        assert host_check == "0.0.0.0"
        assert self.bcserver is not None
        self.bcthread = self.bcserver.runInThread()
        self.old_bcPort = config.NS_BCPORT
        self.old_nsPort = config.NS_PORT
        self.old_nsHost = config.NS_HOST
        config.NS_PORT = self.nsUri.port
        config.NS_HOST = self.nsUri.host
        config.NS_BCPORT = self.bcserver.getPort()

    def teardown_method(self):
        time.sleep(0.01)
        self.nameserver.shutdown()
        self.bcserver.close()
        self.bcthread.join()
        config.NS_HOST = self.old_nsHost
        config.NS_PORT = self.old_nsPort
        config.NS_BCPORT = self.old_bcPort

    def testBCLookup0000(self):
        ns = Pyro5.core.locate_ns()  # broadcast lookup
        assert isinstance(ns, Pyro5.client.Proxy)
        assert ns._pyroUri.host != "0.0.0.0"
        ns._pyroRelease()
