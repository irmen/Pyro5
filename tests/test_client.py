import copy
import pytest
import time
import Pyro5.client
import Pyro5.errors
from Pyro5 import config


class TestProxy:
    def testBasics(self):
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


class TestRemoteMethod:

    class BatchProxyMock(object):
        def __init__(self):
            self.result = []
            self._pyroMaxRetries = 0

        def __copy__(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def _pyroClaimOwnership(self):
            pass

        def _pyroInvokeBatch(self, calls, oneway=False):
            self.result = []
            for methodname, args, kwargs in calls:
                if methodname == "error":
                    self.result.append(Pyro5.core._ExceptionWrapper(ValueError("some exception")))
                    break  # stop processing the rest, this is what Pyro should do in case of an error in a batch
                elif methodname == "pause":
                    time.sleep(args[0])
                self.result.append("INVOKED %s args=%s kwargs=%s" % (methodname, args, kwargs))
            if oneway:
                return
            else:
                return self.result

    def testBatchMethod(self):
        proxy = self.BatchProxyMock()
        batch = Pyro5.client.BatchProxy(proxy)
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
        batch = Pyro5.client.BatchProxy(proxy)
        assert batch.foo(42) is None
        assert batch.bar("abc") is None
        assert batch.baz(42, "abc", arg=999) is None
        assert batch.error() is None  # generate an exception
        assert batch.foo(42) is None  # this call should not be performed after the error
        results = batch(oneway=True)
        assert results is None  # oneway always returns None
        assert len(proxy.result) == 4  # should have done 4 calls, not 5

    def testBatchMethodReuse(self):
        proxy = self.BatchProxyMock()
        batch = Pyro5.client.BatchProxy(proxy)
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
