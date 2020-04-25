"""
Tests for a running Pyro server, without timeouts.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import time
import threading
import serpent
import pytest
import Pyro5.core
import Pyro5.client
import Pyro5.server
import Pyro5.errors
import Pyro5.serializers
import Pyro5.protocol
import Pyro5.callcontext
import Pyro5.socketutil
from Pyro5 import config
from support import *


@Pyro5.server.expose
class ServerTestObject(object):
    something = 99
    dict_attr = {}

    def __init__(self):
        self._dictionary = {"number": 42}
        self.dict_attr = {"number2": 43}
        self._value = 12345

    def getDict(self):
        return self._dictionary

    def getDictAttr(self):
        return self.dict_attr

    def multiply(self, x, y):
        return x * y

    def divide(self, x, y):
        return x // y

    def ping(self):
        pass

    def echo(self, obj):
        return obj

    def blob(self, blob):
        return blob.info, blob.deserialized()

    @Pyro5.server.oneway
    def oneway_delay(self, delay):
        time.sleep(delay)

    def delay(self, delay):
        time.sleep(delay)
        return "slept %d seconds" % delay

    def delayAndId(self, delay, id):
        time.sleep(delay)
        return "slept for " + str(id)

    def testargs(self, x, *args, **kwargs):
        return [x, list(args), kwargs]  # don't return tuples, this enables us to test json serialization as well.

    def nonserializableException(self):
        raise NonserializableError(("xantippe", lambda x: 0))

    @Pyro5.server.oneway
    def oneway_multiply(self, x, y):
        return x * y

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, newvalue):
        self._value = newvalue

    @property
    def dictionary(self):
        return self._dictionary

    def iterator(self):
        return iter(["one", "two", "three"])

    def generator(self):
        yield "one"
        yield "two"
        yield "three"
        yield "four"
        yield "five"

    def response_annotation(self):
        # part of the annotations tests
        if "XYZZ" not in Pyro5.callcontext.current_context.annotations:
            raise ValueError("XYZZ should be present in annotations in the daemon")
        if Pyro5.callcontext.current_context.annotations["XYZZ"] != b"data from proxy via new api":
            raise ValueError("XYZZ annotation has wrong data")
        Pyro5.callcontext.current_context.response_annotations["ANN2"] = b"daemon annotation via new api"
        return {"annotations_in_daemon": Pyro5.callcontext.current_context.annotations}

    def new_test_object(self):
        return ServerTestObject()


class NotEverythingExposedClass(object):
    def __init__(self, name):
        self.name = name

    @Pyro5.server.expose
    def getName(self):
        return self.name

    def unexposed(self):
        return "you should not see this"    # .... only when REQUIRE_EXPOSE is set to True is this valid


class DaemonLoopThread(threading.Thread):
    def __init__(self, pyrodaemon):
        super().__init__()
        self.setDaemon(True)
        self.pyrodaemon = pyrodaemon
        self.running = threading.Event()
        self.running.clear()

    def run(self):
        self.running.set()
        try:
            self.pyrodaemon.requestLoop()
        except Pyro5.errors.CommunicationError:
            pass  # ignore pyro communication errors


class DaemonWithSabotagedHandshake(Pyro5.server.Daemon):
    def _handshake(self, conn, denied_reason=None):
        # receive the client's handshake data
        msg = Pyro5.protocol.recv_stub(conn, [Pyro5.protocol.MSG_CONNECT])
        # return a CONNECTFAIL always
        serializer = Pyro5.serializers.serializers_by_id[msg.serializer_id]
        data = serializer.dumps("rigged connection failure")
        msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_CONNECTFAIL, 0, 1, serializer.serializer_id, data)
        conn.send(msg.data)
        return False


class TestServerBrokenHandshake:
    def setup_method(self):
        config.LOGWIRE = True
        self.daemon = DaemonWithSabotagedHandshake(port=0)
        obj = ServerTestObject()
        uri = self.daemon.register(obj, "something")
        self.objectUri = uri
        self.daemonthread = DaemonLoopThread(self.daemon)
        self.daemonthread.start()
        self.daemonthread.running.wait()
        time.sleep(0.05)

    def teardown_method(self):
        time.sleep(0.05)
        self.daemon.shutdown()
        self.daemonthread.join()

    def testDaemonConnectFail(self):
        # check what happens when the daemon responds with a failed connection msg
        with Pyro5.client.Proxy(self.objectUri) as p:
            with pytest.raises(Pyro5.errors.CommunicationError) as x:
                p.ping()
            message = str(x.value)
            assert "rejected:" in message
            assert "rigged connection failure" in message


class TestServerOnce:
    """tests that are fine to run with just a single server type"""

    def setup_method(self):
        config.LOGWIRE = True
        Pyro5.serializers.SerializerBase.register_class_to_dict(ServerTestObject, lambda x: {})
        Pyro5.serializers.SerializerBase.register_dict_to_class("test_server.ServerTestObject", lambda cn, d: ServerTestObject())
        self.daemon = Pyro5.server.Daemon(port=0)
        obj = ServerTestObject()
        uri = self.daemon.register(obj, "something")
        self.objectUri = uri
        obj2 = NotEverythingExposedClass("hello")
        self.daemon.register(obj2, "unexposed")
        self.daemonthread = DaemonLoopThread(self.daemon)
        self.daemonthread.start()
        self.daemonthread.running.wait()
        time.sleep(0.05)

    def teardown_method(self):
        time.sleep(0.05)
        Pyro5.serializers.SerializerBase.unregister_class_to_dict(ServerTestObject)
        Pyro5.serializers.SerializerBase.unregister_dict_to_class("test_server.ServerTestObject")
        if self.daemon is not None:
            self.daemon.shutdown()
            self.daemonthread.join()

    def testPingMessage(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            p._pyroBind()
            conn = p._pyroConnection
            msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_PING, 42, 999, 0, b"something")
            conn.send(msg.data)
            msg = Pyro5.protocol.recv_stub(conn, [Pyro5.protocol.MSG_PING])
            assert msg.type == Pyro5.protocol.MSG_PING
            assert msg.seq == 999
            assert msg.data == b"pong"
            Pyro5.protocol.SendingMessage.ping(p._pyroConnection)  # the convenience method that does the above

    def testSequence(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            p.echo(1)
            p.echo(2)
            p.echo(3)
            assert p._pyroSeq, "should have 3 method calls" == 3
            p._pyroSeq = 999   # hacking the seq nr won't have any effect because it is the reply from the server that is checked
            assert p.echo(42) == 42

    def testMetaOnAttrs(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            assert p.multiply(5, 11) == 55
            # property
            x = p.getDict()
            assert x == {"number": 42}
            p.dictionary.update({"more": 666})  # should not fail because metadata is enabled and the dictionary property is retrieved as local copy
            x = p.getDict()
            assert x == {"number": 42}  # not updated remotely because we had a local copy
        with Pyro5.client.Proxy(self.objectUri) as p:
            with pytest.raises(AttributeError):
                # attribute should fail (meta only works for exposed properties)
                p.dict_attr.update({"more": 666})

    def testSomeArgumentTypes(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            assert p.testargs(1) == [1, [], {}]
            assert p.testargs(1, 2, 3, a=4) == [1, [2, 3], {'a': 4}]
            assert p.testargs(1, **{'a': 2}) == [1, [], {'a': 2}]

    def testUnicodeKwargs(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            assert p.testargs(1, **{chr(65): 2}) == [1, [], {chr(65): 2}]
            result = p.testargs(chr(0x20ac), **{chr(0x20ac): 2})
            assert chr(0x20ac) == result[0]
            key = list(result[2].keys())[0]
            assert chr(0x20ac) == key

    def testNormalProxy(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            assert p.multiply(7, 6) == 42

    def testExceptions(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            with pytest.raises(ZeroDivisionError):
                p.divide(1, 0)
            with pytest.raises(TypeError):
                p.multiply("a", "b")

    def testProxyMetadata(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            # unconnected proxies have empty metadata
            assert p._pyroAttrs == set()
            assert p._pyroMethods == set()
            assert p._pyroOneway == set()
            # connecting it should obtain metadata (as long as METADATA is true)
            p._pyroBind()
            assert p._pyroAttrs == {'value', 'dictionary'}
            assert p._pyroMethods == {'echo', 'getDict', 'divide', 'nonserializableException', 'ping', 'oneway_delay', 'delayAndId', 'delay', 'testargs',
                              'multiply', 'oneway_multiply', 'getDictAttr', 'iterator', 'generator', 'response_annotation', 'blob', 'new_test_object'}
            assert p._pyroOneway == {'oneway_multiply', 'oneway_delay'}
            p._pyroAttrs = None
            p._pyroGetMetadata()
            assert p._pyroAttrs == {'value', 'dictionary'}
            p._pyroAttrs = None
            p._pyroGetMetadata(self.objectUri.object)
            assert p._pyroAttrs == {'value', 'dictionary'}
            p._pyroAttrs = None
            p._pyroGetMetadata(known_metadata={"attrs": set(), "oneway": set(), "methods": {"ping"}})
            assert p._pyroAttrs == set()

    def testProxyAttrsMetadataOn(self):
        # read attributes
        with Pyro5.client.Proxy(self.objectUri) as p:
            # unconnected proxy still has empty metadata.
            # but, as soon as an attribute is used, the metadata is obtained (as long as METADATA is true)
            a = p.value
            assert a == 12345
            a = p.multiply
            assert isinstance(a, Pyro5.client._RemoteMethod)  # multiply is still a regular method
            with pytest.raises(AttributeError):
                _ = p.non_existing_attribute
        # set attributes, should also trigger getting metadata
        with Pyro5.client.Proxy(self.objectUri) as p:
            p.value = 42
            assert p.value == 42
            assert "value" in p._pyroAttrs

    def testProxyAnnotations(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            Pyro5.callcontext.current_context.annotations = {"XYZZ": b"invalid test data"}
            with pytest.raises(ValueError):
                p.response_annotation()
            Pyro5.callcontext.current_context.annotations = {"XYZZ": b"data from proxy via new api"}
            response = p.response_annotation()
            assert Pyro5.callcontext.current_context.response_annotations["ANN2"] == b"daemon annotation via new api"
            # check that the daemon received both the old and the new annotation api data:
            daemon_annotations = response["annotations_in_daemon"]
            assert serpent.tobytes(daemon_annotations["XYZZ"]) == b"data from proxy via new api"

    def testExposedRequired(self):
        with self.daemon.proxyFor("unexposed") as p:
            assert p._pyroMethods == {"getName"}
            assert p.getName() == "hello"
            with pytest.raises(AttributeError) as e:
                p.unexposed()
            expected_msg = "remote object '%s' has no exposed attribute or method 'unexposed'" % p._pyroUri
            assert str(e.value) == expected_msg
            with pytest.raises(AttributeError) as e:
                p.unexposed_set = 999
            expected_msg = "remote object '%s' has no exposed attribute 'unexposed_set'" % p._pyroUri
            assert str(e.value) == expected_msg

    def testProperties(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            _ = p.value
            # metadata should be loaded now
            assert p._pyroAttrs == {"value", "dictionary"}
            with pytest.raises(AttributeError):
                _ = p.something
            with pytest.raises(AttributeError):
                _ = p._dictionary
            with pytest.raises(AttributeError):
                _ = p._value
            assert p.value == 12345
            assert p.dictionary == {"number": 42}

    def testHasAttr(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            # with metadata on, hasattr actually gives proper results
            assert hasattr(p, "multiply")
            assert hasattr(p, "oneway_multiply")
            assert hasattr(p, "value")
            assert not hasattr(p, "_value")
            assert not hasattr(p, "_dictionary")
            assert not hasattr(p, "non_existing_attribute")

    def testProxyMetadataKnown(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            # unconnected proxies have empty metadata
            assert p._pyroAttrs == set()
            assert p._pyroMethods == set()
            assert p._pyroOneway == set()
            # set some metadata manually, they should be overwritten at connection time
            p._pyroMethods = set("abc")
            p._pyroAttrs = set("xyz")
            p._pyroBind()
            assert p._pyroAttrs != set("xyz")
            assert p._pyroMethods != set("abc")
            assert p._pyroOneway != set()

    def testNonserializableException_other(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            with pytest.raises(Pyro5.errors.PyroError) as x:
                p.nonserializableException()
            tblines = "\n".join(Pyro5.errors.get_pyro_traceback(x.type, x.value, x.tb))
            assert "unsupported serialized class" in tblines

    def testBatchProxy(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            batch = Pyro5.client.BatchProxy(p)
            assert batch.multiply(7, 6) is None
            assert batch.divide(999, 3) is None
            assert batch.ping() is None
            assert batch.divide(999, 0) is None    # force an error here
            assert batch.multiply(3, 4) is None    # this call should not be performed anymore
            results = batch()
            assert next(results) == 42
            assert next(results) == 333
            assert next(results) is None
            with pytest.raises(ZeroDivisionError):
                next(results)    # 999//0 should raise this error
            with pytest.raises(StopIteration):
                next(results)    # no more results should be available after the error

    def testBatchOneway(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            batch = Pyro5.client.BatchProxy(p)
            assert batch.multiply(7, 6) is None
            assert batch.delay(1) is None    # a delay shouldn't matter with oneway
            assert batch.multiply(3, 4) is None
            begin = time.time()
            results = batch(oneway=True)
            duration = time.time() - begin
            assert duration < 0.1, "oneway batch with delay should return almost immediately"
            assert results is None

    def testPyroTracebackNormal(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            with pytest.raises(ZeroDivisionError) as x:
                p.divide(999, 0)  # force error here
            # going to check if the magic pyro traceback attribute is available for batch methods too
            tb = "".join(Pyro5.errors.get_pyro_traceback(x.type, x.value, x.tb))
            assert "Remote traceback:" in tb  # validate if remote tb is present
            assert "ZeroDivisionError" in tb  # the error
            assert "return x // y" in tb  # the statement

    def testPyroTracebackBatch(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            batch = Pyro5.client.BatchProxy(p)
            assert batch.divide(999, 0) is None    # force an exception here
            results = batch()
            with pytest.raises(ZeroDivisionError) as x:
                next(results)
            # going to check if the magic pyro traceback attribute is available for batch methods too
            tb = "".join(Pyro5.errors.get_pyro_traceback(x.type, x.value, x.tb))
            assert "Remote traceback:" in tb  # validate if remote tb is present
            assert "ZeroDivisionError" in tb  # the error
            assert "return x // y" in tb  # the statement
            with pytest.raises(StopIteration):
                next(results)  # no more results should be available after the error

    def testAutoProxy(self):
        obj = ServerTestObject()
        with Pyro5.client.Proxy(self.objectUri) as p:
            result = p.echo(obj)
            assert isinstance(result, ServerTestObject), "non-pyro object must be returned as normal class"
            self.daemon.register(obj)
            result = p.echo(obj)
            assert isinstance(result, Pyro5.client.Proxy), "serialized pyro object must be a proxy"
            self.daemon.register(ServerTestObject)
            new_result = result.new_test_object()
            assert isinstance(new_result, Pyro5.client.Proxy), "serialized pyro object must be a proxy"
            self.daemon.unregister(ServerTestObject)
            self.daemon.unregister(obj)
            result = p.echo(obj)
            assert isinstance(result, ServerTestObject), "unregistered pyro object must be normal class again"

    def testConnectOnce(self):
        with Pyro5.client.Proxy(self.objectUri) as proxy:
            assert proxy._pyroBind(), "first bind should always connect"
            assert not proxy._pyroBind(), "second bind should not connect again"

    def testMaxMsgSize(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            bigobject = [42] * 1000
            result = p.echo(bigobject)
            assert bigobject == result
            try:
                config.MAX_MESSAGE_SIZE = 999
                with pytest.raises(Pyro5.errors.ProtocolError):
                    _ = p.echo(bigobject)       # message too large
            finally:
                config.MAX_MESSAGE_SIZE = 1024* 1024* 1024

    def testIterator(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            iterator = p.iterator()
            assert isinstance(iterator, Pyro5.client._StreamResultIterator)
            assert next(iterator) == "one"
            assert next(iterator) == "two"
            assert next(iterator) == "three"
            with pytest.raises(StopIteration):
                next(iterator)
            iterator.close()

    def testGenerator(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            generator = p.generator()
            assert isinstance(generator, Pyro5.client._StreamResultIterator)
            assert next(generator) == "one"
            assert next(generator) == "two"
            assert next(generator) == "three"
            assert next(generator) == "four"
            assert next(generator) == "five"
            with pytest.raises(StopIteration):
                next(generator)
            with pytest.raises(StopIteration):
                next(generator)
            generator.close()
            generator = p.generator()
            _ = [v for v in generator]
            with pytest.raises(StopIteration):
                next(generator)
            generator.close()

    def testCleanup(self):
        p1 = Pyro5.client.Proxy(self.objectUri)
        p2 = Pyro5.client.Proxy(self.objectUri)
        p3 = Pyro5.client.Proxy(self.objectUri)
        p1.echo(42)
        p2.echo(42)
        p3.echo(42)
        # we have several active connections still up, see if we can cleanly shutdown the daemon
        # (it should interrupt the worker's socket connections)
        time.sleep(0.1)
        self.daemon.shutdown()
        self.daemon = None
        p1._pyroRelease()
        p2._pyroRelease()
        p3._pyroRelease()

    def testSerializedBlob(self):
        sb = Pyro5.client.SerializedBlob("blobname", [1, 2, 3])
        assert sb.info == "blobname"
        assert sb.deserialized() == [1, 2, 3]

    def testSerializedBlobMessage(self):
        # XXX todo fix BLOB handling/test
        serializer = Pyro5.serializers.serializers["serpent"]
        data = serializer.dumpsCall("object", "method", ([1, 2, 3],), None)
        msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, serializer.serializer_id, data)
        sb = Pyro5.client.SerializedBlob("blobname", msg, is_blob=True)
        assert sb.info == "blobname"
        assert sb.deserialized() == ([1, 2, 3],)

    def testProxySerializedBlobArg(self):
        # XXX todo fix BLOB handling/test
        with Pyro5.client.Proxy(self.objectUri) as p:
            blobinfo, blobdata = p.blob(Pyro5.client.SerializedBlob("blobname", [1, 2, 3]))
            assert blobinfo == "blobname"
            assert blobdata == [1, 2, 3]

    def testResourceFreeing(self):
        rsvc = ResourceService()
        uri = self.daemon.register(rsvc)
        with Pyro5.client.Proxy(uri) as p:
            p.allocate("r1")
            p.allocate("r2")
            resources = {r.name: r for r in rsvc.resources}
            p.free("r1")
            rsc = p.list()
            assert rsc == ["r2"]
            assert resources["r1"].close_called
            assert not resources["r2"].close_called
        time.sleep(0.02)
        assert resources["r1"].close_called
        assert resources["r2"].close_called
        with Pyro5.client.Proxy(uri) as p:
            rsc = p.list()
            assert rsc == [], "r2 must now be freed due to connection loss earlier"



class TestServerThreadNoTimeout:
    SERVERTYPE = "thread"
    COMMTIMEOUT = None

    def setup_method(self):
        config.LOGWIRE = True
        config.POLLTIMEOUT = 0.1
        config.SERVERTYPE = self.SERVERTYPE
        config.COMMTIMEOUT = self.COMMTIMEOUT
        self.daemon = Pyro5.server.Daemon(port=0)
        obj = ServerTestObject()
        uri = self.daemon.register(obj, "something")
        self.objectUri = uri
        self.daemonthread = DaemonLoopThread(self.daemon)
        self.daemonthread.start()
        self.daemonthread.running.wait()
        time.sleep(0.05)

    def teardown_method(self):
        time.sleep(0.05)
        self.daemon.shutdown()
        self.daemonthread.join()
        config.SERVERTYPE = "thread"
        config.COMMTIMEOUT = None

    def testConnectionStuff(self):
        p1 = Pyro5.client.Proxy(self.objectUri)
        p2 = Pyro5.client.Proxy(self.objectUri)
        assert not p1._pyroConnection
        assert not p2._pyroConnection
        p1.ping()
        p2.ping()
        _ = p1.multiply(11, 5)
        _ = p2.multiply(11, 5)
        assert p1._pyroConnection
        assert p2._pyroConnection
        p1._pyroRelease()
        p1._pyroRelease()
        p2._pyroRelease()
        p2._pyroRelease()
        assert not p1._pyroConnection
        assert not p2._pyroConnection
        p1._pyroBind()
        _ = p1.multiply(11, 5)
        _ = p2.multiply(11, 5)
        assert p1._pyroConnection
        assert p2._pyroConnection
        assert p1._pyroUri.protocol == "PYRO"
        assert p2._pyroUri.protocol == "PYRO"
        p1._pyroRelease()
        p2._pyroRelease()

    def testReconnectAndCompression(self):
        # try reconnects
        with Pyro5.client.Proxy(self.objectUri) as p:
            assert not p._pyroConnection
            p._pyroReconnect(tries=100)
            assert p._pyroConnection
        assert not p._pyroConnection
        # test compression:
        try:
            with Pyro5.client.Proxy(self.objectUri) as p:
                config.COMPRESSION = True
                assert p.multiply(5, 11) == 55
                assert p.multiply("*" * 500, 2) == "*" * 1000
        finally:
            config.COMPRESSION = False

    def testOnewayMetaOn(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            assert p._pyroOneway == set()  # when not bound, no meta info exchange has been done
            p._pyroBind()
            assert "oneway_multiply" in p._pyroOneway  # after binding, meta info has been processed
            assert p.multiply(5, 11) == 55  # not tagged as @Pyro5.oneway
            assert p.oneway_multiply(5, 11) is None   # tagged as @Pyro5.oneway
            p._pyroOneway = set()
            assert p.multiply(5, 11) == 55
            assert p.oneway_multiply(5, 11) == 55
            # check nonexisting method behavoir for oneway methods
            with pytest.raises(AttributeError):
                p.nonexisting_method()
            p._pyroOneway.add("nonexisting_method")
            # now it should still fail because of metadata telling Pyro what methods actually exist
            with pytest.raises(AttributeError):
                p.nonexisting_method()

    def testOnewayWithProxySubclass(self):
        class ProxyWithOneway(Pyro5.client.Proxy):
            def __init__(self, arg):
                super(ProxyWithOneway, self).__init__(arg)
                self._pyroOneway = {"oneway_multiply", "multiply"}

        with ProxyWithOneway(self.objectUri) as p:
            assert p.oneway_multiply(5, 11) is None
            assert p.multiply(5, 11) == 55
            p._pyroOneway = set()
            assert p.oneway_multiply(5, 11) == 55
            assert p.multiply(5, 11) == 55

    def testOnewayDelayed(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            p.ping()
            now = time.time()
            p.oneway_delay(1)  # oneway so we should continue right away
            time.sleep(0.01)
            assert time.time() - now < 0.2, "delay should be running as oneway"
            now = time.time()
            assert p.multiply(5, 11), "expected a normal result from a non-oneway call" == 55
            assert time.time() - now < 0.2, "delay should be running in its own thread"

    def testSerializeConnected(self):
        # online serialization tests
        ser = Pyro5.serializers.serializers[config.SERIALIZER]
        proxy = Pyro5.client.Proxy(self.objectUri)
        proxy._pyroBind()
        assert proxy._pyroConnection
        p = ser.dumps(proxy)
        proxy2 = ser.loads(p)
        assert proxy2._pyroConnection is None
        assert proxy._pyroConnection
        assert proxy._pyroUri == proxy2._pyroUri
        proxy2._pyroBind()
        assert proxy2._pyroConnection
        assert proxy2._pyroConnection is not proxy._pyroConnection
        proxy._pyroRelease()
        proxy2._pyroRelease()
        assert proxy._pyroConnection is None
        assert proxy2._pyroConnection is None
        proxy.ping()
        proxy2.ping()
        # try copying a connected proxy
        import copy
        proxy3 = copy.copy(proxy)
        assert proxy3._pyroConnection is None
        assert proxy._pyroConnection
        assert proxy._pyroUri == proxy3._pyroUri
        assert proxy3._pyroUri is not proxy._pyroUri
        proxy._pyroRelease()
        proxy2._pyroRelease()
        proxy3._pyroRelease()

    def testException(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            with pytest.raises(ZeroDivisionError) as x:
                p.divide(1, 0)
            pyrotb = "".join(Pyro5.errors.get_pyro_traceback(x.type, x.value, x.tb))
            assert "Remote traceback" in pyrotb
            assert "ZeroDivisionError" in pyrotb

    def testTimeoutCall(self):
        config.COMMTIMEOUT = None
        with Pyro5.client.Proxy(self.objectUri) as p:
            p.ping()
            start = time.time()
            p.delay(0.5)
            duration = time.time() - start
            assert 0.4 < duration < 0.6
            p._pyroTimeout = 0.1
            start = time.time()
            with pytest.raises(Pyro5.errors.TimeoutError):
                p.delay(1)
            duration = time.time() - start
            assert duration < 0.3

    def testTimeoutConnect(self):
        # set up a unresponsive daemon
        with Pyro5.server.Daemon(port=0) as d:
            time.sleep(0.5)
            obj = ServerTestObject()
            uri = d.register(obj)
            # we're not going to start the daemon's event loop
            p = Pyro5.client.Proxy(uri)
            p._pyroTimeout = 0.2
            start = time.time()
            with pytest.raises(Pyro5.errors.TimeoutError) as e:
                p.ping()
            assert str(e.value) == "receiving: timeout"

    # XXX todo: add test about proxy thread ownership transfer

    def testServerConnections(self):
        # check if the server allows to grow the number of connections
        proxies = [Pyro5.client.Proxy(self.objectUri) for _ in range(10)]
        try:
            for p in proxies:
                p._pyroTimeout = 0.5
                p._pyroBind()
            for p in proxies:
                p.ping()
        finally:
            for p in proxies:
                p._pyroRelease()

    def testGeneratorProxyClose(self):
        p = Pyro5.client.Proxy(self.objectUri)
        generator = p.generator()
        p._pyroRelease()
        with pytest.raises(Pyro5.errors.ConnectionClosedError):
            next(generator)

    def testGeneratorLinger(self):
        orig_linger = config.ITER_STREAM_LINGER
        orig_commt = config.COMMTIMEOUT
        orig_pollt = config.POLLTIMEOUT
        try:
            config.ITER_STREAM_LINGER = 0.5
            config.COMMTIMEOUT = 0.2
            config.POLLTIMEOUT = 0.2
            p = Pyro5.client.Proxy(self.objectUri)
            generator = p.generator()
            assert next(generator) == "one"
            p._pyroRelease()
            with pytest.raises(Pyro5.errors.ConnectionClosedError):
                next(generator)
            p._pyroReconnect()
            assert next(generator), "generator should resume after reconnect" == "two"
            # check that after the linger time passes, the generator *is* gone
            p._pyroRelease()
            time.sleep(2)
            p._pyroReconnect()
            with pytest.raises(Pyro5.errors.PyroError):  # should not be resumable anymore
                next(generator)
        finally:
            config.ITER_STREAM_LINGER = orig_linger
            config.COMMTIMEOUT = orig_commt
            config.POLLTIMEOUT = orig_pollt

    def testGeneratorNoLinger(self):
        orig_linger = config.ITER_STREAM_LINGER
        try:
            p = Pyro5.client.Proxy(self.objectUri)
            config.ITER_STREAM_LINGER = 0  # disable linger
            generator = p.generator()
            assert next(generator) == "one"
            p._pyroRelease()
            time.sleep(0.2)
            with pytest.raises(Pyro5.errors.ConnectionClosedError):
                next(generator)
            p._pyroReconnect()
            with pytest.raises(Pyro5.errors.PyroError):  # should not be resumable after reconnect
                next(generator)
            generator.close()
        finally:
            config.ITER_STREAM_LINGER = orig_linger


class TestServerMultiplexNoTimeout(TestServerThreadNoTimeout):
    SERVERTYPE = "multiplex"
    COMMTIMEOUT = None

    def testException(self):
        pass
