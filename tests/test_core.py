"""
Tests for the core logic.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import os
import copy
import time
import uuid
import pytest
import importlib
import logging
import Pyro5.core
import Pyro5.callcontext
import Pyro5.client
import Pyro5.errors
import Pyro5.configure
import Pyro5.server
from Pyro5 import config
from support import *


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


# XXXX FROM HERE CONVERTED from Pyro4  test_core  :

    def testConfig(self):
        assert type(config.COMPRESSION) is bool
        assert type(config.NS_PORT) is int
        cfgdict = config.as_dict()
        assert type(cfgdict) is dict
        assert "COMPRESSION" in cfgdict
        assert config.COMPRESSION == cfgdict["COMPRESSION"]

    def testConfigDefaults(self):
        # some security sensitive settings:
        config.reset(False)   # reset the config to default
        assert config.HOST == "localhost"
        assert config.NS_HOST == "localhost"
        assert config.SERIALIZER == "serpent"

    def testConfigValid(self):
        with pytest.raises(AttributeError):
            config.XYZ_FOOBAR = True  # don't want to allow weird config names

    def testConfigParseBool(self):
        config = Pyro5.configure.Configuration()
        assert type(config.COMPRESSION) is bool
        os.environ["PYRO_COMPRESSION"] = "yes"
        config.reset()
        assert config.COMPRESSION
        os.environ["PYRO_COMPRESSION"] = "off"
        config.reset()
        assert not config.COMPRESSION
        os.environ["PYRO_COMPRESSION"] = "foobar"
        with pytest.raises(ValueError):
            config.reset()
        del os.environ["PYRO_COMPRESSION"]
        config.reset()

    def testConfigDump(self):
        config = Pyro5.configure.Configuration()
        dump = config.dump()
        assert "version:" in dump
        assert "LOGLEVEL" in dump

    def testLogInit(self):
        _ = logging.getLogger("Pyro5")
        os.environ["PYRO_LOGLEVEL"] = "DEBUG"
        os.environ["PYRO_LOGFILE"] = "{stderr}"
        importlib.reload(Pyro5)
        _ = logging.getLogger("Pyro5")
        os.environ["PYRO_LOGFILE"] = "Pyro.log"
        importlib.reload(Pyro5)
        _ = logging.getLogger("Pyro5")
        del os.environ["PYRO_LOGLEVEL"]
        del os.environ["PYRO_LOGFILE"]
        importlib.reload(Pyro5)
        _ = logging.getLogger("Pyro5")

    def testUriStrAndRepr(self):
        uri = "PYRONAME:some_obj_name"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri
        uri = "PYRONAME:some_obj_name@host.com"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri + ":" + str(config.NS_PORT)  # a PYRONAME uri with a hostname gets a port too if omitted
        uri = "PYRONAME:some_obj_name@host.com:8888"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri
        expected = "<Pyro5.core.URI at 0x%x; PYRONAME:some_obj_name@host.com:8888>" % id(p)
        assert repr(p) == expected
        uri = "PYRO:12345@host.com:9999"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri
        uri = "PYRO:12345@./u:sockname"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri
        uri = "PYRO:12345@./u:sockname"
        assert str(p) == uri
        assert type(p.sockname) is str
        uri = "PYRO:12345@./u:sock name with strings"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri

    def testUriParsingPyro(self):
        p = Pyro5.core.URI("PYRONAME:some_obj_name")
        assert p.protocol == "PYRONAME"
        assert p.object == "some_obj_name"
        assert p.host is None
        assert p.sockname is None
        assert p.port is None
        p = Pyro5.core.URI("PYRONAME:some_obj_name@host.com:9999")
        assert p.protocol == "PYRONAME"
        assert p.object == "some_obj_name"
        assert p.host == "host.com"
        assert p.port == 9999

        p = Pyro5.core.URI("PYRO:12345@host.com:4444")
        assert p.protocol == "PYRO"
        assert p.object == "12345"
        assert p.host == "host.com"
        assert p.sockname is None
        assert p.port == 4444
        assert p.location == "host.com:4444"
        p = Pyro5.core.URI("PYRO:12345@./u:sockname")
        assert p.object == "12345"
        assert p.sockname == "sockname"
        p = Pyro5.core.URI("PYRO:12345@./u:/tmp/sockname")
        assert p.object == "12345"
        assert p.sockname == "/tmp/sockname"
        p = Pyro5.core.URI("PYRO:12345@./u:/path with spaces/sockname  ")
        assert p.object == "12345"
        assert p.sockname == "/path with spaces/sockname  "
        p = Pyro5.core.URI("PYRO:12345@./u:../sockname")
        assert p.object == "12345"
        assert p.sockname == "../sockname"
        p = Pyro5.core.URI("pyro:12345@host.com:4444")
        assert p.protocol == "PYRO"
        assert p.object == "12345"
        assert p.host == "host.com"
        assert p.sockname is None
        assert p.port == 4444

    def testUriParsingIpv6(self):
        p = Pyro5.core.URI("pyro:12345@[::1]:4444")
        assert p.host == "::1"
        assert p.location == "[::1]:4444"
        with pytest.raises(Pyro5.errors.PyroError) as e:
            Pyro5.core.URI("pyro:12345@[[::1]]:4444")
        assert str(e.value) == "invalid ipv6 address: enclosed in too many brackets"
        with pytest.raises(Pyro5.errors.PyroError) as e:
            Pyro5.core.URI("pyro:12345@[must_be_numeric_here]:4444")
        assert str(e.value) == "invalid ipv6 address: the part between brackets must be a numeric ipv6 address"

    def testUriParsingPyroname(self):
        p = Pyro5.core.URI("PYRONAME:objectname")
        assert p.protocol == "PYRONAME"
        assert p.object == "objectname"
        assert p.host is None
        assert p.port is None
        p = Pyro5.core.URI("PYRONAME:objectname@nameserverhost")
        assert p.protocol == "PYRONAME"
        assert p.object == "objectname"
        assert p.host == "nameserverhost"
        assert p.port == config.NS_PORT  # Pyroname uri with host gets a port too if not specified
        p = Pyro5.core.URI("PYRONAME:objectname@nameserverhost:4444")
        assert p.protocol == "PYRONAME"
        assert p.object == "objectname"
        assert p.host == "nameserverhost"
        assert p.port == 4444
        p = Pyro5.core.URI("PyroName:some_obj_name@host.com:9999")
        assert p.protocol == "PYRONAME"
        p = Pyro5.core.URI("pyroname:some_obj_name@host.com:9999")
        assert p.protocol == "PYRONAME"

    def testUriParsingPyrometa(self):
        p = Pyro5.core.URI("PYROMETA:meta")
        assert p.protocol == "PYROMETA"
        assert p.object == {"meta"}
        assert p.host is None
        assert p.port is None
        p = Pyro5.core.URI("PYROMETA:meta1,meta2,meta2@nameserverhost")
        assert p.protocol == "PYROMETA"
        assert p.object == {"meta1", "meta2"}
        assert p.host == "nameserverhost"
        assert p.port == config.NS_PORT  # PyroMeta uri with host gets a port too if not specified
        p = Pyro5.core.URI("PYROMETA:meta@nameserverhost:4444")
        assert p.protocol == "PYROMETA"
        assert p.object == {"meta"}
        assert p.host == "nameserverhost"
        assert p.port == 4444
        p = Pyro5.core.URI("PyroMeta:meta1,meta2@host.com:9999")
        assert p.protocol == "PYROMETA"
        p = Pyro5.core.URI("PyroMeta:meta1,meta2@host.com:9999")
        assert p.protocol == "PYROMETA"

    def testInvalidUris(self):
        with pytest.raises(TypeError):
            Pyro5.core.URI(None)
        with pytest.raises(TypeError):
            Pyro5.core.URI(99999)
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI(" ")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("a")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYR")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO::")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:a")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:x@")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:x@hostname")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:@hostname:portstr")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:@hostname:7766")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:objid@hostname:7766:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:obj id@hostname:7766")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROLOC:objname")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROLOC:objname@host")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROLOC:objectname@hostname:4444")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRONAME:")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRONAME:obj name@nameserver:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRONAME:objname@nameserver:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRONAME:objname@nameserver:7766:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROMETA:")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROMETA:meta@nameserver:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROMETA:meta@nameserver:7766:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROMETA:meta1, m2 ,m3@nameserver:7766:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("FOOBAR:")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("FOOBAR:objid@hostname:7766")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:12345@./u:sockname:9999")

    def testUriUnicode(self):
        p = Pyro5.core.URI("PYRO:12345@host.com:4444")
        assert p.protocol == "PYRO"
        assert p.object == "12345"
        assert p.host == "host.com"
        assert type(p.protocol) is str
        assert type(p.object) is str
        assert type(p.host) is str
        assert p.sockname is None
        assert p.port == 4444

        uri = "PYRO:12345@hostname:9999"
        p = Pyro5.core.URI(uri)
        unicodeuri = "PYRO:weirdchars" + chr(0x20ac) + "@host" + chr(0x20AC) + ".com:4444"
        pu = Pyro5.core.URI(unicodeuri)
        assert pu.protocol == "PYRO"
        assert pu.host == "host" + chr(0x20AC) + ".com"
        assert pu.object == "weirdchars" + chr(0x20AC)
        assert str(pu) == "PYRO:weirdchars" + chr(0x20ac) + "@host" + chr(0x20ac) + ".com:4444"
        expected = ("<Pyro5.core.URI at 0x%x; PYRO:weirdchars" + chr(0x20ac) + "@host" + chr(0x20ac) + ".com:4444>") % id(pu)
        assert repr(pu) == expected
        assert str(pu) == "PYRO:weirdchars" + chr(0x20ac) + "@host" + chr(0x20ac) + ".com:4444"

    def testUriCopy(self):
        p1 = Pyro5.core.URI("PYRO:12345@hostname:9999")
        p2 = Pyro5.core.URI(p1)
        p3 = copy.copy(p1)
        assert p2.protocol == p1.protocol
        assert p2.host == p1.host
        assert p2.port == p1.port
        assert p2.object == p1.object
        assert p2 == p1
        assert p3.protocol == p1.protocol
        assert p3.host == p1.host
        assert p3.port == p1.port
        assert p3.object == p1.object
        assert p3 == p1

    def testUriSubclassCopy(self):
        class SubURI(Pyro5.core.URI):
            pass
        u = SubURI("PYRO:12345@hostname:9999")
        u2 = copy.copy(u)
        assert isinstance(u2, SubURI)

    def testUriEqual(self):
        p1 = Pyro5.core.URI("PYRO:12345@host.com:9999")
        p2 = Pyro5.core.URI("PYRO:12345@host.com:9999")
        p3 = Pyro5.core.URI("PYRO:99999@host.com:4444")
        assert p2 == p1
        assert p1 != p3
        assert p2 != p3
        assert p1 == p2
        assert p1 != p3
        assert p2 != p3
        assert p1 == p2
        assert p1 != p3
        assert p2 != p3
        assert hash(p1) == hash(p2)
        assert hash(p1) != hash(p3)
        p2.port = 4444
        p2.object = "99999"
        assert p1 != p2
        assert p3 == p2
        assert p1 != p2
        assert p2 == p3
        assert p1 != p2
        assert p2 == p3
        assert hash(p1) != hash(p2)
        assert hash(p2) == hash(p3)
        assert p1 != 42

    def testLocation(self):
        assert Pyro5.core.URI.isUnixsockLocation("./u:name")
        assert not(Pyro5.core.URI.isUnixsockLocation("./p:name"))
        assert not(Pyro5.core.URI.isUnixsockLocation("./x:name"))
        assert not(Pyro5.core.URI.isUnixsockLocation("foobar"))

    def testProxyCopy(self):
        u = Pyro5.core.URI("PYRO:12345@hostname:9999")
        p1 = Pyro5.client.Proxy(u)
        p2 = copy.copy(p1)  # check that most basic copy also works
        assert p2 == p1
        assert p2._pyroOneway == set()
        p1._pyroAttrs = set("abc")
        p1._pyroTimeout = 42
        p1._pyroOneway = set("def")
        p1._pyroMethods = set("ghi")
        p1._pyroHandshake = "apples"
        p2 = copy.copy(p1)
        assert p2 == p1
        assert p2._pyroUri == p1._pyroUri
        assert p2._pyroOneway == p1._pyroOneway
        assert p2._pyroMethods == p1._pyroMethods
        assert p2._pyroAttrs == p1._pyroAttrs
        assert p2._pyroTimeout == p1._pyroTimeout
        assert p2._pyroHandshake == p1._pyroHandshake
        p1._pyroRelease()
        p2._pyroRelease()

    def testProxySubclassCopy(self):
        class ProxySub(Pyro5.client.Proxy):
            pass
        p = ProxySub("PYRO:12345@hostname:9999")
        p2 = copy.copy(p)
        assert isinstance(p2, ProxySub)
        p._pyroRelease()
        p2._pyroRelease()

    # XXX TODO move proxy tests to their own class / test file (proxy is not in core anymore but in client)

    def testBatchProxyAdapterCopy(self):
        with Pyro5.client.Proxy("PYRO:12345@hostname:9999") as proxy:
            batchproxy = Pyro5.client.BatchProxy(proxy)
            p2 = copy.copy(batchproxy)
            assert isinstance(p2, Pyro5.client.BatchProxy)

    def testProxyOffline(self):
        # only offline stuff here.
        # online stuff needs a running daemon, so we do that in another test, to keep this one simple
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.client.Proxy("999")
        p1 = Pyro5.client.Proxy("PYRO:9999@localhost:15555")
        p2 = Pyro5.client.Proxy(Pyro5.core.URI("PYRO:9999@localhost:15555"))
        assert p2._pyroUri == p1._pyroUri
        assert p1._pyroConnection is None
        p1._pyroRelease()
        p1._pyroRelease()
        # try copying a not-connected proxy
        p3 = copy.copy(p1)
        assert p3._pyroConnection is None
        assert p1._pyroConnection is None
        assert p1._pyroUri == p3._pyroUri
        assert p1._pyroUri is not p3._pyroUri
        p3._pyroRelease()

    def testProxySerializerOverride(self):
        serializer = config.SERIALIZER
        try:
            with pytest.raises(ValueError) as x:
                config.SERIALIZER = "~invalid~"
                Pyro5.client.Proxy("PYRO:obj@localhost:5555")
            assert "unknown" in str(x.value)
        finally:
            config.SERIALIZER = serializer
        try:
            with pytest.raises(KeyError) as x:
                proxy = Pyro5.client.Proxy("PYRO:obj@localhost:5555")
                proxy._pyroSerializer = "~invalidoverride~"
                proxy._pyroConnection = "FAKE"
                proxy.methodcall()
            assert "invalidoverride" in str(x.value)
        finally:
            proxy._pyroConnection = None
            config.SERIALIZER = serializer

    def testProxyDirMetadata(self):
        with Pyro5.client.Proxy("PYRO:9999@localhost:15555") as p:
            # metadata isn't loaded
            assert '__hash__' in dir(p)
            assert "ping" not in dir(p)
            # emulate obtaining metadata
            p._pyroAttrs = {"prop"}
            p._pyroMethods = {"ping"}
            assert "__hash__" in dir(p)
            assert "prop" in dir(p)
            assert "ping" in dir(p)

    def testProxySettings(self):
        p1 = Pyro5.client.Proxy("PYRO:9999@localhost:15555")
        p2 = Pyro5.client.Proxy("PYRO:9999@localhost:15555")
        p1._pyroOneway.add("method")
        p1._pyroAttrs.add("attr")
        p1._pyroMethods.add("method2")
        assert "method" in p1._pyroOneway
        assert "attr" in p1._pyroAttrs
        assert "method2" in  p1._pyroMethods
        assert "method" not in p2._pyroOneway
        assert "attr" not in p2._pyroAttrs
        assert "method2" not in p2._pyroMethods
        assert p1._pyroOneway is not p2._pyroOneway, "p1 and p2 should have different oneway tables"
        assert p1._pyroAttrs is not p2._pyroAttrs, "p1 and p2 should have different attr tables"
        assert p1._pyroMethods is not p2._pyroMethods, "p1 and p2 should have different method tables"
        p1._pyroRelease()
        p2._pyroRelease()

    def testProxyWithStmt(self):
        class ConnectionMock(object):
            closeCalled = False
            keep_open = False

            def close(self):
                self.closeCalled = True

        connMock = ConnectionMock()
        # first without a 'with' statement
        p = Pyro5.client.Proxy("PYRO:9999@localhost:15555")
        p._pyroConnection = connMock
        assert not(connMock.closeCalled)
        p._pyroRelease()
        assert p._pyroConnection is None
        assert connMock.closeCalled

        connMock = ConnectionMock()
        with Pyro5.client.Proxy("PYRO:9999@localhost:15555") as p:
            p._pyroConnection = connMock
        assert p._pyroConnection is None
        assert connMock.closeCalled
        connMock = ConnectionMock()
        with pytest.raises(ZeroDivisionError):
            with Pyro5.client.Proxy("PYRO:9999@localhost:15555") as p:
                p._pyroConnection = connMock
                print(1 // 0)  # cause an error
        assert p._pyroConnection is None
        assert connMock.closeCalled
        p = Pyro5.client.Proxy("PYRO:9999@localhost:15555")
        with p:
            assert p._pyroUri
        p._pyroRelease()

    def testNoConnect(self):
        wrongUri = Pyro5.core.URI("PYRO:foobar@localhost:59999")
        with pytest.raises(Pyro5.errors.CommunicationError):
            with Pyro5.client.Proxy(wrongUri) as p:
                p.ping()

    def testTimeoutGetSet(self):
        class ConnectionMock(object):
            def __init__(self):
                self.timeout = config.COMMTIMEOUT
                self.keep_open = False

            def close(self):
                pass

        config.COMMTIMEOUT = None
        p = Pyro5.client.Proxy("PYRO:obj@host:555")
        assert p._pyroTimeout is None
        p._pyroTimeout = 5
        assert p._pyroTimeout == 5
        p = Pyro5.client.Proxy("PYRO:obj@host:555")
        p._pyroConnection = ConnectionMock()
        assert p._pyroTimeout is None
        p._pyroTimeout = 5
        assert p._pyroTimeout == 5
        assert p._pyroConnection.timeout == 5
        config.COMMTIMEOUT = 2
        p = Pyro5.client.Proxy("PYRO:obj@host:555")
        p._pyroConnection = ConnectionMock()
        assert p._pyroTimeout == 2
        assert p._pyroConnection.timeout == 2
        p._pyroTimeout = None
        assert p._pyroTimeout is None
        assert p._pyroConnection.timeout is None
        config.COMMTIMEOUT = None
        p._pyroRelease()

    def testCallbackDecorator(self):
        # just test the decorator itself, testing the callback
        # exception handling is kinda hard in unit tests. Maybe later.
        class Test(object):
            @Pyro5.server.callback
            def method(self):
                pass

            def method2(self):
                pass

        t = Test()
        assert getattr(t.method, "_pyroCallback", False)
        assert not getattr(t.method2, "_pyroCallback", False)

    def testProxyEquality(self):
        p1 = Pyro5.client.Proxy("PYRO:thing@localhost:15555")
        p2 = Pyro5.client.Proxy("PYRO:thing@localhost:15555")
        p3 = Pyro5.client.Proxy("PYRO:other@machine:16666")
        assert p1 == p2
        assert not(p1 != p2)
        assert not(p1 == p3)
        assert p1 != p3
        assert hash(p1) == hash(p2)
        assert not(hash(p1) == hash(p3))
        assert not(p1 == 42)
        assert p1 != 42
        p1._pyroRelease()
        p2._pyroRelease()
        p3._pyroRelease()

    def testCallContext(self):
        ctx = Pyro5.callcontext.current_context
        corr_id = uuid.UUID('1897022f-c481-4117-a4cc-cbd1ca100582')
        ctx.correlation_id = corr_id
        d = ctx.to_global()
        assert isinstance(d, dict)
        assert d["correlation_id"] == corr_id
        corr_id2 = uuid.UUID('67b05ad9-2d6a-4ed8-8ed5-95cba68b4cf9')
        d["correlation_id"] = corr_id2
        ctx.from_global(d)
        assert Pyro5.callcontext.current_context.correlation_id == corr_id2
        Pyro5.callcontext.current_context.correlation_id = None


# XXX move to server tests?

class ExposeDecoratorTests:
    # note: the bulk of the tests for the @expose decorator are found in the test_util module
    def testExposeInstancemodeDefault(self):
        @Pyro5.server.expose
        class TestClassOne:
            def method(self):
                pass
        class TestClassTwo:
            @Pyro5.server.expose
            def method(self):
                pass
        class TestClassThree:
            def method(self):
                pass
        with Pyro5.server.Daemon() as daemon:
            daemon.register(TestClassOne)
            daemon.register(TestClassTwo)
            daemon.register(TestClassThree)
            assert TestClassOne._pyroInstancing == ("session", None)
            assert TestClassTwo._pyroInstancing == ("session", None)
            assert TestClassThree._pyroInstancing == ("session", None)


class BehaviorDecoratorTests:
    def testBehaviorInstancemodeInvalid(self):
        with pytest.raises(ValueError):
            @Pyro5.server.behavior(instance_mode="kaputt")
            class TestClass:
                def method(self):
                    pass

    def testBehaviorRequiresParams(self):
        with pytest.raises(SyntaxError) as x:
            @Pyro5.server.behavior
            class TestClass:
                def method(self):
                    pass
        assert "is missing argument" in str(x)

    def testBehaviorInstancecreatorInvalid(self):
        with pytest.raises(TypeError):
            @Pyro5.server.behavior(instance_creator=12345)
            class TestClass:
                def method(self):
                    pass

    def testBehaviorOnMethodInvalid(self):
        with pytest.raises(TypeError):
            class TestClass:
                @Pyro5.server.behavior(instance_mode="~invalidmode~")
                def method(self):
                    pass
        with pytest.raises(TypeError):
            class TestClass:
                @Pyro5.server.behavior(instance_mode="percall", instance_creator=float)
                def method(self):
                    pass
        with pytest.raises(TypeError):
            class TestClass:
                @Pyro5.server.behavior()
                def method(self):
                    pass

    def testBehaviorInstancing(self):
        @Pyro5.server.behavior(instance_mode="percall", instance_creator=float)
        class TestClass:
            def method(self):
                pass
        im, ic = TestClass._pyroInstancing
        assert im == "percall"
        assert ic is float

    def testBehaviorWithExposeKeepsCorrectValues(self):
        @Pyro5.server.behavior(instance_mode="percall", instance_creator=float)
        @Pyro5.server.expose
        class TestClass:
            pass
        im, ic = TestClass._pyroInstancing
        assert im == "percall"
        assert ic is float

        @Pyro5.server.expose
        @Pyro5.server.behavior(instance_mode="percall", instance_creator=float)
        class TestClass2:
            pass
        im, ic = TestClass2._pyroInstancing
        assert im == "percall"
        assert ic is float


class RemoteMethodTests:
    def testBatchMethod(self):
        proxy = self.BatchProxyMock()
        batch = Pyro5.client.batch(proxy)
        assert batch.foo(42) is None
        assert batch.bar("abc") is None
        assert batch.baz(42, "abc", arg=999) is None
        assert batch.error() is None  # generate an exception
        assert batch.foo(42) is None  # this call should not be performed after the error
        results = batch()
        result = next(results)
        assert result == "INVOKED foo args=(42,) kwargs={}"
        result = next(results)
        assert result == "INVOKED bar args=('abc',) kwargs={}"
        result = next(results)
        assert result == "INVOKED baz args=(42, 'abc') kwargs={'arg': 999}"
        with pytest.raises(ValueError):
            next(results)
        with pytest.raises(StopIteration):
            next(results)
        assert len(proxy.result) == 4  # should have done 4 calls, not 5
        batch._pyroRelease()

    def testBatchMethodOneway(self):
        proxy = self.BatchProxyMock()
        batch = Pyro5.client.batch(proxy)
        assert batch.foo(42) is None
        assert batch.bar("abc") is None
        assert batch.baz(42, "abc", arg=999) is None
        assert batch.error() is None  # generate an exception
        assert batch.foo(42) is None  # this call should not be performed after the error
        results = batch(oneway=True)
        assert results is None  # oneway always returns None
        assert len(proxy.result) == 4  # should have done 4 calls, not 5
        with pytest.raises(Pyro5.errors.PyroError):
            batch(oneway=True, asynchronous=True)

    def testBatchMethodAsync(self):
        proxy = self.BatchProxyMock()
        batch = Pyro5.core.batch(proxy)
        assert batch.foo(42) is None
        assert batch.bar("abc") is None
        assert batch.pause(0.5) is None  # pause shouldn't matter with asynchronous
        assert batch.baz(42, "abc", arg=999) is None
        begin = time.time()
        asyncresult = batch(asynchronous=True)
        duration = time.time() - begin
        self.assertLess(duration, 0.2, "batch oneway with pause should still return almost immediately")
        results = asyncresult.value
        assert len(proxy.result) == 4  # should have done 4 calls
        result = next(results)
        assert result == "INVOKED foo args=(42,) kwargs={}"
        result = next(results)
        assert result == "INVOKED bar args=('abc',) kwargs={}"
        result = next(results)
        assert result == "INVOKED pause args=(0.5,) kwargs={}"
        result = next(results)
        assert result == "INVOKED baz args=(42, 'abc') kwargs={'arg': 999}"
        with pytest.raises(StopIteration):
            next(results)  # and now there should not be any more results

    def testBatchMethodReuse(self):
        proxy = self.BatchProxyMock()
        batch = Pyro5.core.batch(proxy)
        batch.foo(1)
        batch.foo(2)
        results = batch()
        assert list(results) == ['INVOKED foo args=(1,) kwargs={}', 'INVOKED foo args=(2,) kwargs={}']
        # re-use the batch proxy:
        batch.foo(3)
        batch.foo(4)
        results = batch()
        assert list(results) == ['INVOKED foo args=(3,) kwargs={}', 'INVOKED foo args=(4,) kwargs={}']
        results = batch()
        assert len(list(results)) == 0

# XXX todo move to server

class TestSimpleServe:
    class DaemonWrapper(Pyro5.server.Daemon):
        def requestLoop(self, *args):
            # override with empty method to fall out of the serveSimple call
            pass

    def testSimpleServeLegacy(self):
        with TestSimpleServe.DaemonWrapper() as d:
            o1 = MyThingPartlyExposed(1)
            o2 = MyThingPartlyExposed(2)
            objects = {o1: "test.o1", o2: None}
            Pyro5.server.Daemon.serveSimple(objects, daemon=d, ns=False, verbose=False)
            assert len(d.objectsById) == 3
            assert "test.o1" in d.objectsById
            assert o1 in d.objectsById.values()
            assert o2 in d.objectsById.values()

    def testSimpleServe(self):
        with TestSimpleServe.DaemonWrapper() as d:
            o1 = MyThingPartlyExposed(1)
            o2 = MyThingPartlyExposed(2)
            objects = {o1: "test.o1", o2: None}
            Pyro5.server.serve(objects, daemon=d, use_ns=False, verbose=False)
            assert len(d.objectsById) == 3
            assert "test.o1" in d.objectsById
            assert o1 in d.objectsById.values()
            assert o2 in d.objectsById.values()

    def testSimpleServeSameNamesLegacy(self):
        with TestSimpleServe.DaemonWrapper() as d:
            o1 = MyThingPartlyExposed(1)
            o2 = MyThingPartlyExposed(2)
            o3 = MyThingPartlyExposed(3)
            objects = {o1: "test.name", o2: "test.name", o3: "test.othername"}
            with pytest.raises(Pyro5.errors.DaemonError):
                Pyro5.server.Daemon.serveSimple(objects, daemon=d, ns=False, verbose=False)

    def testSimpleServeSameNames(self):
        with TestSimpleServe.DaemonWrapper() as d:
            o1 = MyThingPartlyExposed(1)
            o2 = MyThingPartlyExposed(2)
            o3 = MyThingPartlyExposed(3)
            objects = {o1: "test.name", o2: "test.name", o3: "test.othername"}
            with pytest.raises(Pyro5.errors.DaemonError):
                Pyro5.server.serve(objects, daemon=d, use_ns=False, verbose=False)
