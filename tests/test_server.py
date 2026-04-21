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
        self.items = list("qwerty")

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

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, item):
        return self.items[item]


class NotEverythingExposedClass(object):
    def __init__(self, name):
        self.name = name

    @Pyro5.server.expose
    def getName(self):
        return self.name

    def unexposed(self):
        return "you should not see this"


class DaemonLoopThread(threading.Thread):
    def __init__(self, pyrodaemon):
        super().__init__()
        self.daemon = True
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
        config.SERIALIZER = "serpent"
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
            # connecting it should obtain metadata
            p._pyroBind()
            assert p._pyroAttrs == {'value', 'dictionary'}
            assert p._pyroMethods == {'echo', 'getDict', 'divide', 'nonserializableException', 'ping', 'oneway_delay', 'delayAndId', 'delay', 'testargs',
                              'multiply', 'oneway_multiply', 'getDictAttr', 'iterator', 'generator', 'response_annotation', 'blob', 'new_test_object',
                              '__iter__', '__len__', '__getitem__'}
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
            # but, as soon as an attribute is used, the metadata is obtained
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

    def testRegisterWeak(self):
        obj=ServerTestObject()
        uri=self.daemon.register(obj,weak=True)
        with Pyro5.client.Proxy(uri) as p:
            result = p.getDict()
            assert isinstance(result, dict), "getDict() is proxied normally"
            del obj # weak registration should not prevent the obj from being garbage-collected
            with pytest.raises(Pyro5.errors.DaemonError):
                result = p.getDict()

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

    def testLenAndIterAndIndexing(self):
        with Pyro5.client.Proxy(self.objectUri) as p:
            assert len(p) == 6
            values = list(iter(p))
            assert values == ['q', 'w', 'e', 'r', 't', 'y']
            assert p[0] == 'q'
            assert p[1] == 'w'
            assert p[2] == 'e'
            assert p[3] == 'r'
            assert p[4] == 't'
            assert p[5] == 'y'
            with pytest.raises(IndexError):
                _ = p[6]

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
        serializer = Pyro5.serializers.serializers["serpent"]
        data = serializer.dumpsCall("object", "method", ([1, 2, 3],), {"kwarg": 42})
        msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, serializer.serializer_id, data)
        sb = Pyro5.client.SerializedBlob("blobname", msg, is_blob=True)
        assert sb.info == "blobname"
        assert sb.deserialized() == ([1, 2, 3], )

    def testProxySerializedBlobArg(self):
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
        config.SERIALIZER = "serpent"
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
            assert p.multiply(5, 11) == 55  # not tagged as @Pyro5.server.oneway
            assert p.oneway_multiply(5, 11) is None   # tagged as @Pyro5.server.oneway
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


class TestMetaAndExpose:
    def testBasic(self):
        o = MyThingFullExposed("irmen")
        m1 = Pyro5.server._get_exposed_members(o)
        m2 = Pyro5.server._get_exposed_members(MyThingFullExposed)
        assert m1 == m2
        keys = m1.keys()
        assert len(keys) == 3
        assert "methods" in keys
        assert "attrs" in keys
        assert "oneway" in keys

    def testGetExposedCacheWorks(self):
        class Thingy(object):
            def method1(self):
                pass
            @property
            def prop(self):
                return 1
            def notexposed(self):
                pass
        m1 = Pyro5.server._get_exposed_members(Thingy, only_exposed=False)
        def new_method(self, arg):
            return arg
        Thingy.new_method = new_method
        m2 = Pyro5.server._get_exposed_members(Thingy, only_exposed=False)
        assert m2, "should still be equal because result from cache" == m1

    def testPrivateNotExposed(self):
        o = MyThingFullExposed("irmen")
        m = Pyro5.server._get_exposed_members(o)
        assert m["methods"] == {"classmethod", "staticmethod", "method", "__dunder__", "oneway", "exposed"}
        assert m["attrs"] == {"prop1", "readonly_prop1", "prop2"}
        assert m["oneway"] == {"oneway"}
        o = MyThingPartlyExposed("irmen")
        m = Pyro5.server._get_exposed_members(o)
        assert m["methods"] == {"oneway", "exposed"}
        assert m["attrs"] == {"prop1", "readonly_prop1"}
        assert m["oneway"] == {"oneway"}

    def testNotOnlyExposed(self):
        o = MyThingPartlyExposed("irmen")
        m = Pyro5.server._get_exposed_members(o, only_exposed=False)
        assert m["methods"] == {"classmethod", "staticmethod", "method", "__dunder__", "oneway", "exposed"}
        assert m["attrs"] == {"prop1", "readonly_prop1", "prop2"}
        assert m["oneway"] == {"oneway"}

    def testPartlyExposedSubclass(self):
        o = MyThingPartlyExposedSub("irmen")
        m = Pyro5.server._get_exposed_members(o)
        assert m["attrs"] == {"prop1", "readonly_prop1"}
        assert m["oneway"] == {"oneway"}
        assert m["methods"] == {"sub_exposed", "exposed", "oneway"}

    def testExposedSubclass(self):
        o = MyThingExposedSub("irmen")
        m = Pyro5.server._get_exposed_members(o)
        assert m["attrs"] == {"readonly_prop1", "prop1", "prop2"}
        assert m["oneway"] == {"oneway", "oneway2"}
        assert m["methods"] == {"classmethod", "staticmethod", "oneway", "__dunder__", "method", "exposed",
                                "oneway2", "sub_exposed", "sub_unexposed"}

    def testExposePrivateFails(self):
        with pytest.raises(AttributeError):
            class Test1(object):
                @Pyro5.server.expose
                def _private(self):
                    pass
        with pytest.raises(AttributeError):
            class Test3(object):
                @Pyro5.server.expose
                def __private(self):
                    pass
        with pytest.raises(AttributeError):
            @Pyro5.server.expose
            class _Test4(object):
                pass
        with pytest.raises(AttributeError):
            @Pyro5.server.expose
            class __Test5(object):
                pass

    def testExposeDunderOk(self):
        class Test1(object):
            @Pyro5.server.expose
            def __dunder__(self):
                pass
        assert Test1.__dunder__._pyroExposed
        @Pyro5.server.expose
        class Test2(object):
            def __dunder__(self):
                pass
        assert Test2._pyroExposed
        assert Test2.__dunder__._pyroExposed

    def testClassmethodExposeWrongOrderFail(self):
        with pytest.raises(AttributeError) as ax:
            class TestClass:
                @Pyro5.server.expose
                @classmethod
                def cmethod(cls):
                    pass
        assert "must be done after" in str(ax.value)
        with pytest.raises(AttributeError) as ax:
            class TestClass:
                @Pyro5.server.expose
                @staticmethod
                def smethod(cls):
                    pass
        assert "must be done after" in str(ax.value)

    def testClassmethodExposeCorrectOrderOkay(self):
        class TestClass:
            @classmethod
            @Pyro5.server.expose
            def cmethod(cls):
                pass
            @staticmethod
            @Pyro5.server.expose
            def smethod(cls):
                pass
        assert TestClass.cmethod._pyroExposed
        assert TestClass.smethod._pyroExposed

    def testGetExposedProperty(self):
        o = MyThingFullExposed("irmen")
        with pytest.raises(AttributeError):
            Pyro5.server._get_exposed_property_value(o, "name")
        with pytest.raises(AttributeError):
            Pyro5.server._get_exposed_property_value(o, "c_attr")
        with pytest.raises(AttributeError):
            Pyro5.server._get_exposed_property_value(o, "propvalue")
        with pytest.raises(AttributeError):
            Pyro5.server._get_exposed_property_value(o, "unexisting_attribute")
        assert Pyro5.server._get_exposed_property_value(o, "prop1") == 42
        assert Pyro5.server._get_exposed_property_value(o, "prop2") == 42

    def testGetExposedPropertyFromPartiallyExposed(self):
        o = MyThingPartlyExposed("irmen")
        with pytest.raises(AttributeError):
            Pyro5.server._get_exposed_property_value(o, "name")
        with pytest.raises(AttributeError):
            Pyro5.server._get_exposed_property_value(o, "c_attr")
        with pytest.raises(AttributeError):
            Pyro5.server._get_exposed_property_value(o, "propvalue")
        with pytest.raises(AttributeError):
            Pyro5.server._get_exposed_property_value(o, "unexisting_attribute")
        assert Pyro5.server._get_exposed_property_value(o, "prop1") == 42
        with pytest.raises(AttributeError):
            Pyro5.server._get_exposed_property_value(o, "prop2")

    def testSetExposedProperty(self):
        o = MyThingFullExposed("irmen")
        with pytest.raises(AttributeError):
            Pyro5.server._set_exposed_property_value(o, "name", "erorr")
        with pytest.raises(AttributeError):
            Pyro5.server._set_exposed_property_value(o, "unexisting_attribute", 42)
        with pytest.raises(AttributeError):
            Pyro5.server._set_exposed_property_value(o, "readonly_prop1", 42)
        with pytest.raises(AttributeError):
            Pyro5.server._set_exposed_property_value(o, "propvalue", 999)
        assert o.prop1 == 42
        assert o.prop2 == 42
        Pyro5.server._set_exposed_property_value(o, "prop1", 999)
        assert o.propvalue == 999
        Pyro5.server._set_exposed_property_value(o, "prop2", 8888)
        assert o.propvalue == 8888

    def testSetExposedPropertyFromPartiallyExposed(self):
        o = MyThingPartlyExposed("irmen")
        with pytest.raises(AttributeError):
            Pyro5.server._set_exposed_property_value(o, "name", "erorr")
        with pytest.raises(AttributeError):
            Pyro5.server._set_exposed_property_value(o, "unexisting_attribute", 42)
        with pytest.raises(AttributeError):
            Pyro5.server._set_exposed_property_value(o, "readonly_prop1", 42)
        with pytest.raises(AttributeError):
            Pyro5.server._set_exposed_property_value(o, "propvalue", 999)
        assert o.prop1 == 42
        assert o.prop2 == 42
        Pyro5.server._set_exposed_property_value(o, "prop1", 999)
        assert o.propvalue == 999
        with pytest.raises(AttributeError):
            Pyro5.server._set_exposed_property_value(o, "prop2", 8888)

    def testIsPrivateName(self):
        assert Pyro5.server.is_private_attribute("_")
        assert Pyro5.server.is_private_attribute("__")
        assert Pyro5.server.is_private_attribute("___")
        assert Pyro5.server.is_private_attribute("_p")
        assert Pyro5.server.is_private_attribute("_pp")
        assert Pyro5.server.is_private_attribute("_p_")
        assert Pyro5.server.is_private_attribute("_p__")
        assert Pyro5.server.is_private_attribute("__p")
        assert Pyro5.server.is_private_attribute("___p")
        assert not Pyro5.server.is_private_attribute("__dunder__")  # dunder methods should not be private except a list of exceptions as tested below
        assert Pyro5.server.is_private_attribute("__init__")
        assert Pyro5.server.is_private_attribute("__new__")
        assert Pyro5.server.is_private_attribute("__del__")
        assert Pyro5.server.is_private_attribute("__repr__")
        assert Pyro5.server.is_private_attribute("__str__")
        assert Pyro5.server.is_private_attribute("__format__")
        assert Pyro5.server.is_private_attribute("__nonzero__")
        assert Pyro5.server.is_private_attribute("__bool__")
        assert Pyro5.server.is_private_attribute("__coerce__")
        assert Pyro5.server.is_private_attribute("__cmp__")
        assert Pyro5.server.is_private_attribute("__eq__")
        assert Pyro5.server.is_private_attribute("__ne__")
        assert Pyro5.server.is_private_attribute("__lt__")
        assert Pyro5.server.is_private_attribute("__gt__")
        assert Pyro5.server.is_private_attribute("__le__")
        assert Pyro5.server.is_private_attribute("__ge__")
        assert Pyro5.server.is_private_attribute("__hash__")
        assert Pyro5.server.is_private_attribute("__dir__")
        assert Pyro5.server.is_private_attribute("__enter__")
        assert Pyro5.server.is_private_attribute("__exit__")
        assert Pyro5.server.is_private_attribute("__copy__")
        assert Pyro5.server.is_private_attribute("__deepcopy__")
        assert Pyro5.server.is_private_attribute("__sizeof__")
        assert Pyro5.server.is_private_attribute("__getattr__")
        assert Pyro5.server.is_private_attribute("__setattr__")
        assert Pyro5.server.is_private_attribute("__hasattr__")
        assert Pyro5.server.is_private_attribute("__delattr__")
        assert Pyro5.server.is_private_attribute("__getattribute__")
        assert Pyro5.server.is_private_attribute("__instancecheck__")
        assert Pyro5.server.is_private_attribute("__subclasscheck__")
        assert Pyro5.server.is_private_attribute("__subclasshook__")
        assert Pyro5.server.is_private_attribute("__getinitargs__")
        assert Pyro5.server.is_private_attribute("__getnewargs__")
        assert Pyro5.server.is_private_attribute("__getstate__")
        assert Pyro5.server.is_private_attribute("__setstate__")
        assert Pyro5.server.is_private_attribute("__reduce__")
        assert Pyro5.server.is_private_attribute("__reduce_ex__")

    def testResolveAttr(self):
        @Pyro5.server.expose
        class Exposed(object):
            def __init__(self, value):
                self.propvalue = value
                self.__value__ = value   # is not affected by the @expose

            def __str__(self):
                return "<%s>" % self.value

            def _p(self):
                return "should not be allowed"

            def __p(self):
                return "should not be allowed"

            def __p__(self):
                return "should be allowed (dunder)"

            @property
            def value(self):
                return self.propvalue

        class Unexposed(object):
            def __init__(self):
                self.value = 42

            def __value__(self):
                return self.value

        obj = Exposed("hello")
        obj.a = Exposed("a")
        obj.a.b = Exposed("b")
        obj.a.b.c = Exposed("c")
        obj.a._p = Exposed("p1")
        obj.a._p.q = Exposed("q1")
        obj.a.__p = Exposed("p2")
        obj.a.__p.q = Exposed("q2")
        obj.u = Unexposed()
        obj.u.v = Unexposed()
        # check the accessible attributes
        assert str(Pyro5.server._get_attribute(obj, "a")) == "<a>"
        dunder = str(Pyro5.server._get_attribute(obj, "__p__"))
        assert dunder.startswith("<bound method ")  # dunder is not private, part 1 of the check
        assert "Exposed.__p__ of" in dunder  # dunder is not private, part 2 of the check
        # check what should not be accessible
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "value")
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "propvalue")
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "__value__")  # is not affected by the @expose
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "_p")  # private
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "__p")  # private
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "a.b")
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "a.b.c")
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "a.b.c.d")
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "a._p")
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "a._p.q")
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "a.__p.q")
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "u")
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "u.v")
        with pytest.raises(AttributeError):
            Pyro5.server._get_attribute(obj, "u.v.value")


class TestSimpleServe:
    class DaemonWrapper(Pyro5.server.Daemon):
        def requestLoop(self, *args):
            # override with empty method to fall out of the serve() call
            pass

    def testSimpleServeLegacy(self):
        with TestSimpleServe.DaemonWrapper() as d:
            o1 = MyThingPartlyExposed(1)
            o2 = MyThingPartlyExposed(2)
            objects = {o1: "test.o1", o2: None}
            Pyro5.server.serve(objects, daemon=d, use_ns=False, verbose=False)
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
                Pyro5.server.serve(objects, daemon=d, use_ns=False, verbose=False)

    def testSimpleServeSameNames(self):
        with TestSimpleServe.DaemonWrapper() as d:
            o1 = MyThingPartlyExposed(1)
            o2 = MyThingPartlyExposed(2)
            o3 = MyThingPartlyExposed(3)
            objects = {o1: "test.name", o2: "test.name", o3: "test.othername"}
            with pytest.raises(Pyro5.errors.DaemonError):
                Pyro5.server.serve(objects, daemon=d, use_ns=False, verbose=False)


class TestExposeDecorator:
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


class TestBehaviorDecorator:
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
        assert "is missing argument" in str(x.value)

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
