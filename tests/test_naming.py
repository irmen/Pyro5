"""
Tests for the name server.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import time
import pytest
import threading
import os
import sys
from io import StringIO
import Pyro5.core
import Pyro5.client
import Pyro5.nsc
import Pyro5.nameserver
import Pyro5.socketutil
from Pyro5.errors import CommunicationError, NamingError, PyroError
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
                _ = ns.namespace.keys
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


class TestOfflineNameServer:
    def setup_method(self):
        self.storageProvider = Pyro5.nameserver.MemoryStorage()

    def teardown_method(self):
        self.clearStorage()
        self.clearStorage()
        self.storageProvider.close()

    def clearStorage(self):
        try:
            self.storageProvider.clear()
        except AttributeError:
            pass   # workaround for weird pypy3 issue on Travis

    def testRegister(self):
        ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
        self.clearStorage()
        ns.ping()
        ns.register("test.object1", "PYRO:000000@host.com:4444")
        ns.register("test.object2", "PYRO:222222@host.com:4444")
        ns.register("test.object3", "PYRO:333333@host.com:4444")
        assert str(ns.lookup("test.object1")) == "PYRO:000000@host.com:4444"
        ns.register("test.object1", "PYRO:111111@host.com:4444")  # registering again should be ok by default
        assert str(ns.lookup("test.object1")), "should be new uri" == "PYRO:111111@host.com:4444"
        ns.register("test.sub.objectA", Pyro5.core.URI("PYRO:AAAAAA@host.com:4444"))
        ns.register("test.sub.objectB", Pyro5.core.URI("PYRO:BBBBBB@host.com:4444"))

        # if safe=True, a registration of an existing name should give a NamingError
        with pytest.raises(NamingError):
            ns.register("test.object1", "PYRO:X@Y:5555", safe=True)
        with pytest.raises(TypeError):
            ns.register(None, None)
        with pytest.raises(TypeError):
            ns.register(4444, 4444)
        with pytest.raises(TypeError):
            ns.register("test.wrongtype", 4444)
        with pytest.raises(TypeError):
            ns.register(4444, "PYRO:X@Y:5555")
        with pytest.raises(NamingError):
            ns.lookup("unknown_object")

        uri = ns.lookup("test.object3")
        assert uri == Pyro5.core.URI("PYRO:333333@host.com:4444")  # lookup always returns URI
        ns.remove("unknown_object")
        ns.remove("test.object1")
        ns.remove("test.object2")
        ns.remove("test.object3")
        all_objs = ns.list()
        assert len(all_objs) == 2  # 2 leftover objects
        with pytest.raises(PyroError):
            ns.register("test.nonurivalue", "THISVALUEISNOTANURI")
        ns.storage.close()

    def testRemove(self):
        ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
        self.clearStorage()
        ns.register(Pyro5.core.NAMESERVER_NAME, "PYRO:nameserver@host:555")
        for i in range(20):
            ns.register("test.%d" % i, "PYRO:obj@host:555")
        assert len(ns.list()) == 21
        assert ns.remove("wrong") == 0
        assert ns.remove(prefix="wrong") == 0
        assert ns.remove(regex="wrong.*") == 0
        assert ns.remove("test.0") == 1
        assert len(ns.list()) == 20
        assert ns.remove(prefix="test.1") == 11  # 1, 10-19
        assert ns.remove(regex=r"test\..") == 8  # 2-9
        assert len(ns.list()) == 1
        ns.storage.close()

    def testRemoveProtected(self):
        ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
        self.clearStorage()
        ns.register(Pyro5.core.NAMESERVER_NAME, "PYRO:nameserver@host:555")
        assert ns.remove(Pyro5.core.NAMESERVER_NAME) == 0
        assert ns.remove(prefix="Pyro") == 0
        assert ns.remove(regex="Pyro.*") == 0
        assert Pyro5.core.NAMESERVER_NAME in ns.list()
        ns.storage.close()

    def testUnicodeNames(self):
        ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
        self.clearStorage()
        uri = Pyro5.core.URI("PYRO:unicode" + chr(0x20ac) + "@host:5555")
        ns.register("unicodename" + chr(0x20ac), uri)
        x = ns.lookup("unicodename" + chr(0x20ac))
        assert x == uri
        ns.storage.close()

    def testList(self):
        ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
        self.clearStorage()
        ns.register("test.objects.1", "PYRONAME:something1")
        ns.register("test.objects.2", "PYRONAME:something2")
        ns.register("test.objects.3", "PYRONAME:something3")
        ns.register("test.other.a", "PYRONAME:somethingA")
        ns.register("test.other.b", "PYRONAME:somethingB")
        ns.register("test.other.c", "PYRONAME:somethingC")
        ns.register("entirely.else", "PYRONAME:meh")
        objects = ns.list()
        assert len(objects) == 7
        objects = ns.list(prefix="nothing")
        assert len(objects) == 0
        objects = ns.list(prefix="test.")
        assert len(objects) == 6
        objects = ns.list(regex=r".+other..")
        assert len(objects) == 3
        assert "test.other.a" in objects
        assert objects["test.other.a"] == "PYRONAME:somethingA"
        objects = ns.list(regex=r"\d\d\d\d\d\d\d\d\d\d")
        assert len(objects) == 0
        with pytest.raises(NamingError):
            ns.list(regex="((((((broken")
        ns.storage.close()

    def testNameserverWithStmt(self):
        ns = Pyro5.nameserver.NameServerDaemon(port=0)
        assert ns.nameserver is not None
        ns.close()
        assert ns.nameserver is None
        with Pyro5.nameserver.NameServerDaemon(port=0) as ns:
            assert ns.nameserver is not None
            pass
        assert ns.nameserver is None
        with pytest.raises(ZeroDivisionError):
            with Pyro5.nameserver.NameServerDaemon(port=0) as ns:
                assert ns.nameserver is not None
                print(1 // 0)  # cause an error
        assert ns.nameserver is None
        ns = Pyro5.nameserver.NameServerDaemon(port=0)
        with ns:
            pass
        with pytest.raises(PyroError):
            with ns:
                pass
        ns.close()

    def testStartNSfunc(self):
        myIpAddress = Pyro5.socketutil.get_ip_address("", workaround127=True)
        uri1, ns1, bc1 = Pyro5.nameserver.start_ns(host=myIpAddress, port=0, bcport=0, enableBroadcast=False)
        uri2, ns2, bc2 = Pyro5.nameserver.start_ns(host=myIpAddress, port=0, bcport=0, enableBroadcast=True)
        assert isinstance(uri1, Pyro5.core.URI)
        assert isinstance(ns1, Pyro5.nameserver.NameServerDaemon)
        assert bc1 is None
        assert isinstance(bc2, Pyro5.nameserver.BroadcastServer)
        sock = bc2.sock
        assert hasattr(sock, "fileno")
        _ = bc2.processRequest
        ns1.close()
        ns2.close()
        bc2.close()

    def testNSmain(self):
        oldstdout = sys.stdout
        oldstderr = sys.stderr
        try:
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            with pytest.raises(SystemExit):
                Pyro5.nameserver.main(["--invalidarg"])
            assert "usage" in sys.stderr.getvalue()
            sys.stderr.truncate(0)
            sys.stdout.truncate(0)
            with pytest.raises(SystemExit):
                Pyro5.nameserver.main(["-h"])
            assert "show this help message" in sys.stdout.getvalue()
        finally:
            sys.stdout = oldstdout
            sys.stderr = oldstderr

    def testNSCmain(self):
        oldstdout = sys.stdout
        oldstderr = sys.stderr
        try:
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            with pytest.raises(SystemExit):
                Pyro5.nsc.main(["--invalidarg"])
            assert "usage" in sys.stderr.getvalue()
            sys.stderr.truncate(0)
            sys.stdout.truncate(0)
            with pytest.raises(SystemExit):
                Pyro5.nsc.main(["-h"])
            assert "show this help message" in sys.stdout.getvalue()
        finally:
            sys.stdout = oldstdout
            sys.stderr = oldstderr

    def testNSCfunctions(self):
        oldstdout = sys.stdout
        ns = None
        try:
            sys.stdout = StringIO()
            ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
            with pytest.raises(KeyError):
                Pyro5.nsc.handle_command(ns, "foo", [])
            assert sys.stdout.getvalue().startswith("Error: KeyError ")
            Pyro5.nsc.handle_command(ns, "ping", [])
            assert sys.stdout.getvalue().endswith("ping ok.\n")
            with pytest.raises(NamingError):
                Pyro5.nsc.handle_command(ns, "lookup", ["WeirdName"])
            assert sys.stdout.getvalue().endswith("Error: NamingError - unknown name: WeirdName\n")
            Pyro5.nsc.handle_command(ns, "list", [])
            assert sys.stdout.getvalue().endswith("END LIST \n")
            Pyro5.nsc.handle_command(ns, "listmatching", ["name.$"])
            assert sys.stdout.getvalue().endswith("END LIST - regex 'name.$'\n")
            assert "name1" not in sys.stdout.getvalue()
            Pyro5.nsc.handle_command(ns, "register", ["name1", "PYRO:obj1@hostname:9999"])
            assert sys.stdout.getvalue().endswith("Registered name1\n")
            Pyro5.nsc.handle_command(ns, "remove", ["name2"])
            assert sys.stdout.getvalue().endswith("Nothing removed\n")
            Pyro5.nsc.handle_command(ns, "listmatching", ["name.$"])
            assert "name1 --> PYRO:obj1@hostname:9999" in sys.stdout.getvalue()
            # Pyro5.nsc.handle_command(ns, None, ["removematching", "name.?"])  #  can't be tested, required user input
        finally:
            sys.stdout = oldstdout
            if ns:
                ns.storage.close()

    def testNAT(self):
        uri, ns, bc = Pyro5.nameserver.start_ns(host="", port=0, enableBroadcast=True, nathost="nathosttest", natport=12345)
        assert uri.location == "nathosttest:12345"
        assert ns.uriFor("thing").location == "nathosttest:12345"
        assert bc.nsUri.location != "nathosttest:12345", "broadcast location must not be the NAT location"
        ns.close()
        bc.close()

    def testMetadataRegisterInvalidTypes(self):
        ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
        with pytest.raises(TypeError):
            ns.register("meta1", "PYRO:meta1@localhost:1111", metadata=12345)   # metadata must be iterable
        with pytest.raises(TypeError):
            ns.register("meta1", "PYRO:meta1@localhost:1111", metadata="string")   # metadata must not be str

    def testMetadataLookupInvalidTypes(self):
        ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
        with pytest.raises(TypeError):
            ns.yplookup(meta_all=12345)
        with pytest.raises(TypeError):
            ns.yplookup(meta_all="string")
        with pytest.raises(TypeError):
            ns.yplookup(meta_any=12345)
        with pytest.raises(TypeError):
            ns.yplookup(meta_any="string")

    def testMetadata(self):
        self.clearStorage()
        ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
        # register some names with metadata, and perform simple lookups
        ns.register("meta1", "PYRO:meta1@localhost:1111", metadata={"a", "b", "c"})
        ns.register("meta2", "PYRO:meta2@localhost:2222", metadata={"x", "y", "z"})
        ns.register("meta3", "PYRO:meta3@localhost:3333", metadata=["p", "q", "r", "r", "q"])
        uri = ns.lookup("meta1")
        assert uri.object == "meta1"
        uri, metadata = ns.lookup("meta1", return_metadata=True)
        assert uri.object == "meta1"
        assert set(metadata) == {"a", "b", "c"}
        uri = ns.lookup("meta2")
        assert uri.object == "meta2"
        uri, metadata = ns.lookup("meta2", return_metadata=True)
        assert uri.object == "meta2"
        assert set(metadata) == {"x", "y", "z"}
        uri, metadata = ns.lookup("meta3", return_metadata=True)
        assert uri.object == "meta3"
        assert isinstance(metadata, set)
        assert set(metadata) == {"p", "q", "r"}
        # get a list of everything, without and with metadata
        reg = ns.list()
        assert reg == {'meta1': 'PYRO:meta1@localhost:1111', 'meta2': 'PYRO:meta2@localhost:2222', 'meta3': 'PYRO:meta3@localhost:3333'}
        reg = ns.list(return_metadata=True)
        uri1, meta1 = reg["meta1"]
        uri2, meta2 = reg["meta2"]
        assert uri1 == "PYRO:meta1@localhost:1111"
        assert set(meta1) == {"a", "b", "c"}
        assert uri2 == "PYRO:meta2@localhost:2222"
        assert set(meta2) == {"x", "y", "z"}
        # filter on metadata subset
        reg = ns.yplookup(meta_all={"a", "c"}, return_metadata=False)
        assert len(reg) == 1
        assert reg["meta1"] == "PYRO:meta1@localhost:1111"
        reg = ns.yplookup(meta_all={"a", "c"}, return_metadata=True)
        assert len(reg) == 1
        uri1, meta1 = reg["meta1"]
        assert uri1 == "PYRO:meta1@localhost:1111"
        assert set(meta1) == {"a", "b", "c"}
        reg = ns.yplookup(meta_all={"a", "wrong"})
        assert reg == {}
        reg = ns.yplookup(meta_all={"a", "b", "c", "wrong"})
        assert reg == {}
        reg = ns.yplookup(meta_all={"a", "c", "x"})
        assert reg == {}
        # update some metadata
        with pytest.raises(NamingError):
            ns.set_metadata("notexistingname", set())
        ns.set_metadata("meta1", {"one", "two", "three"})
        uri, meta = ns.lookup("meta1", return_metadata=True)
        assert set(meta) == {"one", "two", "three"}
        # check that a collection is converted to a set
        ns.set_metadata("meta1", ["one", "two", "three", "three", "two"])
        uri, meta = ns.lookup("meta1", return_metadata=True)
        assert isinstance(meta, set)
        assert set(meta) == {"one", "two", "three"}
        # remove record that has some metadata
        ns.remove("meta1")
        ns.remove("meta3")
        assert list(ns.list().keys()) == ["meta2"]
        # other list filters
        reg = ns.list(prefix="meta", return_metadata=True)
        assert len(reg) == 1
        assert set(reg["meta2"][1]) == {"x", "y", "z"}
        reg = ns.list(regex="meta2.*", return_metadata=True)
        assert len(reg) == 1
        assert set(reg["meta2"][1]) == {"x", "y", "z"}
        assert ns.count() == 1

    def testMetadataAny(self):
        self.clearStorage()
        ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
        # register some names with metadata, and perform simple lookups
        ns.register("meta1", "PYRO:meta1@localhost:1111", metadata={"a", "b", "c"})
        ns.register("meta2", "PYRO:meta2@localhost:2222", metadata={"x", "y", "z"})
        ns.register("meta3", "PYRO:meta3@localhost:2222", metadata={"k", "l", "m"})
        result = ns.yplookup(meta_any={"1", "2", "3"})
        assert result == {}
        result = ns.yplookup(meta_any={"1", "2", "a"})
        assert len(result) == 1
        assert "meta1" in result
        result = ns.yplookup(meta_any={"1", "2", "a", "z"})
        assert len(result) == 2
        assert "meta1" in result
        assert "meta2" in result

    def testEmptyMetadata(self):
        self.clearStorage()
        ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
        # register some names with metadata, and perform simple lookups
        ns.register("meta1", "PYRO:meta1@localhost:1111", metadata=set())
        uri, meta = ns.lookup("meta1", return_metadata=True)
        assert meta == set()
        registrations = ns.list(return_metadata=True)
        for name in registrations:
            uri, meta = registrations[name]
            assert meta == set()
        ns.set_metadata("meta1", set())

    def testListNoMultipleFilters(self):
        ns = Pyro5.nameserver.NameServer(storageProvider=self.storageProvider)
        with pytest.raises(ValueError):
            ns.list(prefix="a", regex="a")
        with pytest.raises(ValueError):
            ns.yplookup(meta_any={"a"}, meta_all={"a"})


class TestOfflineNameServerTestsSqlStorage(TestOfflineNameServer):
    def setup_method(self):
        super().setup_method()
        self.storageProvider = Pyro5.nameserver.SqlStorage("pyro-test.sqlite")

    def teardown_method(self):
        try:
            super().teardown_method()
        except AttributeError:
            pass   # workaround for weird pypy3 issue on Travis
        import glob
        for file in glob.glob("pyro-test.sqlite*"):
            os.remove(file)
