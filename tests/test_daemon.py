"""
Tests for the daemon.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import time
import socket
import uuid
import pytest
import Pyro5.core
import Pyro5.client
import Pyro5.server
import Pyro5.nameserver
import Pyro5.protocol
import Pyro5.socketutil
import Pyro5.serializers
from Pyro5.errors import DaemonError, PyroError
from Pyro5 import config
from Pyro5.callcontext import current_context
from support import *


class MyObj(object):
    def __init__(self, arg):
        self.arg = arg

    def __eq__(self, other):
        return self.arg == other.arg

    __hash__ = object.__hash__


class CustomDaemonInterface(Pyro5.server.DaemonObject):
    def __init__(self, daemon):
        super(CustomDaemonInterface, self).__init__(daemon)

    def custom_daemon_method(self):
        return 42


class TestDaemon:
    # We create a daemon, but notice that we are not actually running the requestloop.
    # 'on-line' tests are all taking place in another test, to keep this one simple.

    def setUp(self):
        config.POLLTIMEOUT = 0.1

    def sendHandshakeMessage(self, conn, correlation_id=None):
        ser = Pyro5.serializers.serializers_by_id[Pyro5.serializers.MarshalSerializer.serializer_id]
        data = ser.dumps({"handshake": "hello", "object": Pyro5.core.DAEMON_NAME})
        current_context.correlation_id = correlation_id
        msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_CONNECT, 0, 99, Pyro5.serializers.MarshalSerializer.serializer_id, data)
        conn.send(msg.data)

    def testSerializerAccepted(self):
        with Pyro5.server.Daemon(port=0) as d:
            msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 0, Pyro5.serializers.MarshalSerializer.serializer_id, b"")
            cm = ConnectionMock(msg)
            d.handleRequest(cm)
            msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 0, Pyro5.serializers.JsonSerializer.serializer_id, b"")
            cm = ConnectionMock(msg)
            d.handleRequest(cm)
            msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 0, Pyro5.serializers.SerpentSerializer.serializer_id, b"")
            cm = ConnectionMock(msg)
            d.handleRequest(cm)
            if "msgpack" in Pyro5.serializers.serializers:
                msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 0, Pyro5.serializers.MsgpackSerializer.serializer_id, b"")
                cm = ConnectionMock(msg)
                d.handleRequest(cm)

    def testDaemon(self):
        with Pyro5.server.Daemon(port=0) as d:
            hostname, port = d.locationStr.split(":")
            port = int(port)
            assert Pyro5.core.DAEMON_NAME in d.objectsById
            assert str(d.uriFor(Pyro5.core.DAEMON_NAME)) == "PYRO:" + Pyro5.core.DAEMON_NAME + "@" + d.locationStr
            # check the string representations
            expected = "<Pyro5.server.Daemon at 0x%x; %s - %s; 1 objects>" % (id(d), d.locationStr, Pyro5.socketutil.family_str(d.sock))
            assert str(d) == expected
            assert repr(d) == expected
            sockname = d.sock.getsockname()
            assert sockname[1] == port
            daemonobj = d.objectsById[Pyro5.core.DAEMON_NAME]
            daemonobj.ping()
            daemonobj.registered()

    def testDaemonCustomInterface(self):
        with Pyro5.server.Daemon(port=0, interface=CustomDaemonInterface) as d:
            obj = d.objectsById[Pyro5.core.DAEMON_NAME]
            assert obj.custom_daemon_method() == 42

    def testDaemonConnectedSocket(self):
        try:
            Pyro5.config.SERVERTYPE = "thread"
            with Pyro5.server.Daemon() as d:
                assert "Thread" in d.transportServer.__class__.__name__
            s1, s2 = socket.socketpair()
            with Pyro5.server.Daemon(connected_socket=s1) as d:
                assert d.locationStr=="./u:<<not-bound>>" or d.locationStr.startswith("127.0.")
                assert not("Thread" in d.transportServer.__class__.__name__)
                assert "Existing" in d.transportServer.__class__.__name__
            Pyro5.config.SERVERTYPE = "multiplex"
            with Pyro5.server.Daemon() as d:
                assert "Multiplex" in d.transportServer.__class__.__name__
            s1, s2 = socket.socketpair()
            with Pyro5.server.Daemon(connected_socket=s1) as d:
                assert d.locationStr=="./u:<<not-bound>>" or d.locationStr.startswith("127.0.")
                assert not("Multiplex" in d.transportServer.__class__.__name__)
                assert "Existing" in d.transportServer.__class__.__name__
        finally:
            Pyro5.config.SERVERTYPE = "thread"

    def testDaemonUnixSocket(self):
        if hasattr(socket, "AF_UNIX"):
            SOCKNAME = "test_unixsocket"
            with Pyro5.server.Daemon(unixsocket=SOCKNAME) as d:
                locationstr = "./u:" + SOCKNAME
                assert d.locationStr == locationstr
                assert str(d.uriFor(Pyro5.core.DAEMON_NAME)) == "PYRO:" + Pyro5.core.DAEMON_NAME + "@" + locationstr
                # check the string representations
                expected = "<Pyro5.server.Daemon at 0x%x; %s - Unix; 1 objects>" % (id(d), locationstr)
                assert str(d) == expected
                assert d.sock.getsockname() == SOCKNAME
                assert d.sock.family == socket.AF_UNIX

    def testDaemonUnixSocketAbstractNS(self):
        if hasattr(socket, "AF_UNIX"):
            SOCKNAME = "\0test_unixsocket"  # mind the \0 at the start, for a Linux abstract namespace socket
            with Pyro5.server.Daemon(unixsocket=SOCKNAME) as d:
                locationstr = "./u:" + SOCKNAME
                assert d.locationStr == locationstr
                assert str(d.uriFor(Pyro5.core.DAEMON_NAME)) == "PYRO:" + Pyro5.core.DAEMON_NAME + "@" + locationstr
                # check the string representations
                expected = "<Pyro5.server.Daemon at 0x%x; %s - Unix; 1 objects>" % (id(d), locationstr)
                assert str(d) == expected
                sn_bytes = bytes(SOCKNAME, "ascii")
                assert d.sock.getsockname() == sn_bytes
                assert d.sock.family == socket.AF_UNIX

    def testServertypeThread(self):
        old_servertype = config.SERVERTYPE
        config.SERVERTYPE = "thread"
        with Pyro5.server.Daemon(port=0) as d:
            assert d.sock in d.sockets, "daemon's socketlist should contain the server socket"
            assert len(d.sockets) == 1, "daemon without connections should have just 1 socket"
        config.SERVERTYPE = old_servertype

    def testServertypeMultiplex(self):
        old_servertype = config.SERVERTYPE
        config.SERVERTYPE = "multiplex"
        with Pyro5.server.Daemon(port=0) as d:
            assert d.sock in d.sockets, "daemon's socketlist should contain the server socket"
            assert len(d.sockets) == 1, "daemon without connections should have just 1 socket"
        config.SERVERTYPE = old_servertype

    def testServertypeFoobar(self):
        old_servertype = config.SERVERTYPE
        config.SERVERTYPE = "foobar"
        try:
            with pytest.raises(PyroError):
                Pyro5.server.Daemon()
        finally:
            config.SERVERTYPE = old_servertype

    def testRegisterTwice(self):
        with Pyro5.server.Daemon(port=0) as d:
            o1 = MyObj("object1")
            d.register(o1)
            with pytest.raises(DaemonError) as x:
                d.register(o1)
            assert str(x.value) == "object or class already has a Pyro id"
            d.unregister(o1)
            d.register(o1, "samename")
            o2 = MyObj("object2")
            with pytest.raises(DaemonError) as x:
                d.register(o2, "samename")
            assert str(x.value) == "an object or class is already registered with that id"
            assert hasattr(o1, "_pyroId")
            assert hasattr(o1, "_pyroDaemon")
            d.unregister(o1)
            assert not(hasattr(o1, "_pyroId"))
            assert not(hasattr(o1, "_pyroDaemon"))
            o1._pyroId = "FOOBAR"
            with pytest.raises(DaemonError) as x:
                d.register(o1)
            assert str(x.value) == "object or class already has a Pyro id"
            o1._pyroId = ""
            d.register(o1)  # with empty-string _pyroId register should work

    def testRegisterTwiceForced(self):
        with Pyro5.server.Daemon(port=0) as d:
            o1 = MyObj("object1")
            d.register(o1, "name1")
            d.register(o1, "name2", force=True)
            d.register(o1, "name1", force=True)
            assert d.objectsById["name1"] is d.objectsById["name2"]
            d.unregister(o1)
            o1._pyroId = "FOOBAR_ID"
            d.register(o1, "newname", force=True)
            assert o1._pyroId == "newname"
            assert "newname" in d.objectsById

    def testRegisterEtc(self):
        with Pyro5.server.Daemon(port=0) as d:
            assert len(d.objectsById) == 1
            o1 = MyObj("object1")
            o2 = MyObj("object2")
            d.register(o1)
            with pytest.raises(DaemonError):
                d.register(o2, Pyro5.core.DAEMON_NAME)  # cannot use daemon name
            d.register(o2, "obj2a")

            assert len(d.objectsById) == 3
            assert d.objectsById[o1._pyroId] == o1
            assert d.objectsById["obj2a"] == o2
            assert o2._pyroId == "obj2a"
            assert o2._pyroDaemon == d

            # test unregister
            d.unregister("unexisting_thingie")
            with pytest.raises(ValueError):
                d.unregister(None)
            d.unregister("obj2a")
            d.unregister(o1._pyroId)
            assert len(d.objectsById) == 1
            assert o1._pyroId not in d.objectsById
            assert o2._pyroId not in d.objectsById

            # test unregister objects
            del o2._pyroId
            d.register(o2)
            objectid = o2._pyroId
            assert objectid in d.objectsById
            assert len(d.objectsById) == 2
            d.unregister(o2)
            # no more _pyro attributes must remain after unregistering
            for attr in vars(o2):
                assert not(attr.startswith("_pyro"))
            assert len(d.objectsById) == 1
            assert objectid not in d.objectsById
            with pytest.raises(DaemonError):
                d.unregister([1,2,3])

            # test unregister daemon name
            d.unregister(Pyro5.core.DAEMON_NAME)
            assert Pyro5.core.DAEMON_NAME in d.objectsById

            # weird args
            w = MyObj("weird")
            with pytest.raises(AttributeError):
                d.register(None)
            with pytest.raises(AttributeError):
                d.register(4444)
            with pytest.raises(TypeError):
                d.register(w, 666)

            # uri return value from register
            uri = d.register(MyObj("xyz"))
            assert isinstance(uri, Pyro5.core.URI)
            uri = d.register(MyObj("xyz"), "test.register")
            assert uri.object == "test.register"

    def testRegisterClass(self):
        with Pyro5.server.Daemon(port=0) as d:
            assert len(d.objectsById) == 1
            d.register(MyObj)
            with pytest.raises(DaemonError):
                d.register(MyObj)
            assert len(d.objectsById) == 2
            d.uriFor(MyObj)
            # unregister:
            d.unregister(MyObj)
            assert len(d.objectsById) == 1

    def testRegisterUnicode(self):
        with Pyro5.server.Daemon(port=0) as d:
            myobj1 = MyObj("hello1")
            myobj3 = MyObj("hello3")
            uri1 = d.register(myobj1, "str_name")
            uri3 = d.register(myobj3, "unicode_" + chr(0x20ac))
            assert len(d.objectsById) == 3
            uri = d.uriFor(myobj1)
            assert uri == uri1
            _ = Pyro5.client.Proxy(uri)
            uri = d.uriFor(myobj3)
            assert uri == uri3
            _ = Pyro5.client.Proxy(uri)
            uri = d.uriFor("str_name")
            assert uri == uri1
            _ = Pyro5.client.Proxy(uri)
            _ = Pyro5.client.Proxy(uri)
            uri = d.uriFor("unicode_" + chr(0x20ac))
            assert uri == uri3
            _ = Pyro5.client.Proxy(uri)

    def testDaemonObject(self):
        with Pyro5.server.Daemon(port=0) as d:
            daemon = Pyro5.server.DaemonObject(d)
            obj1 = MyObj("object1")
            obj2 = MyObj("object2")
            obj3 = MyObj("object2")
            d.register(obj1, "obj1")
            d.register(obj2, "obj2")
            d.register(obj3)
            daemon.ping()
            registered = daemon.registered()
            assert type(registered) is list
            assert len(registered) == 4
            assert "obj1" in registered
            assert "obj2" in registered
            assert obj3._pyroId in registered
            d.shutdown()

    def testUriFor(self):
        d = Pyro5.server.Daemon(port=0)
        try:
            o1 = MyObj("object1")
            o2 = MyObj("object2")
            with pytest.raises(DaemonError):
                d.uriFor(o1)
            with pytest.raises(DaemonError):
                d.uriFor(o2)
            d.register(o1, None)
            d.register(o2, "object_two")
            o3 = MyObj("object3")
            with pytest.raises(DaemonError):
                d.uriFor(o3)  # can't get an uri for an unregistered object (note: unregistered name is ok)
            u1 = d.uriFor(o1)
            u2 = d.uriFor(o2._pyroId)
            u3 = d.uriFor("unexisting_thingie")  # unregistered name is no problem, it's just an uri we're requesting
            u4 = d.uriFor(o2)
            assert type(u1) == Pyro5.core.URI
            assert u1.protocol == "PYRO"
            assert u2.protocol == "PYRO"
            assert u3.protocol == "PYRO"
            assert u4.protocol == "PYRO"
            assert u4.object == "object_two"
            assert u3 == Pyro5.core.URI("PYRO:unexisting_thingie@" + d.locationStr)
        finally:
            d.close()

    def testDaemonWithStmt(self):
        d = Pyro5.server.Daemon()
        assert d.transportServer
        d.close()  # closes the transportserver and sets it to None
        assert d.transportServer is None
        with Pyro5.server.Daemon() as d:
            assert d.transportServer
            pass
        assert d.transportServer is None
        with pytest.raises(ZeroDivisionError):
            with Pyro5.server.Daemon() as d:
                print(1 // 0)  # cause an error
        assert d.transportServer is None
        d = Pyro5.server.Daemon()
        with d:
            pass
        with pytest.raises(Pyro5.errors.PyroError):
            with d:
                pass
        d.close()

    def testRequestloopCondition(self):
        with Pyro5.server.Daemon(port=0) as d:
            condition = lambda: False
            start = time.time()
            d.requestLoop(loopCondition=condition)  # this should return almost immediately
            duration = time.time() - start
            assert duration < 0.4

    def testSimpleHandshake(self):
        conn = ConnectionMock()
        with Pyro5.server.Daemon(port=0) as d:
            self.sendHandshakeMessage(conn)
            success = d._handshake(conn)
            assert success
            msg = Pyro5.protocol.recv_stub(conn)
            assert msg.type == Pyro5.protocol.MSG_CONNECTOK
            assert msg.seq == 99

    def testHandshakeDenied(self):
        class HandshakeFailDaemon(Pyro5.server.Daemon):
            def validateHandshake(self, conn, data):
                raise ValueError("handshake fail validation error")
        conn = ConnectionMock()
        with HandshakeFailDaemon(port=0) as d:
            self.sendHandshakeMessage(conn)
            success = d._handshake(conn)
            assert not(success)
            msg = Pyro5.protocol.recv_stub(conn)
            assert msg.type == Pyro5.protocol.MSG_CONNECTFAIL
            assert msg.seq == 99
            assert b"handshake fail validation error" in msg.data
        with Pyro5.server.Daemon(port=0) as d:
            self.sendHandshakeMessage(conn)
            success = d._handshake(conn, denied_reason="no way, handshake denied")
            assert not(success)
            msg = Pyro5.protocol.recv_stub(conn)
            assert msg.type == Pyro5.protocol.MSG_CONNECTFAIL
            assert msg.seq == 99
            assert b"no way, handshake denied" in msg.data

    def testCustomHandshake(self):
        conn = ConnectionMock()
        class CustomHandshakeDaemon(Pyro5.server.Daemon):
            def validateHandshake(self, conn, data):
                return ["sure", "have", "fun"]
            def annotations(self):
                return {"XYZZ": b"custom annotation set by daemon"}
        with CustomHandshakeDaemon(port=0) as d:
            corr_id = uuid.uuid4()
            self.sendHandshakeMessage(conn, correlation_id=corr_id)
            assert current_context.correlation_id == corr_id
            success = d._handshake(conn)
            assert success
            msg = Pyro5.protocol.recv_stub(conn)
            assert msg.type == Pyro5.protocol.MSG_CONNECTOK
            assert msg.seq == 99
            assert len(msg.annotations) == 1
            assert msg.annotations["XYZZ"] == b"custom annotation set by daemon"
            ser = Pyro5.serializers.serializers_by_id[msg.serializer_id]
            data = ser.loads(msg.data)
            assert data["handshake"] == ["sure", "have", "fun"]

    def testNAT(self):
        with Pyro5.server.Daemon() as d:
            assert d.natLocationStr is None
        with Pyro5.server.Daemon(nathost="nathosttest", natport=12345) as d:
            assert d.natLocationStr == "nathosttest:12345"
            assert d.natLocationStr != d.locationStr
            uri = d.register(MyObj(1))
            assert uri.location == "nathosttest:12345"
            uri = d.uriFor("object")
            assert uri.location == "nathosttest:12345"
            uri = d.uriFor("object", nat=False)
            assert uri.location != "nathosttest:12345"
            d = Pyro5.server.Daemon(nathost="bla")
            assert d.natLocationStr.startswith("bla:")
        with pytest.raises(ValueError):
            Pyro5.server.Daemon(natport=5555)
        with pytest.raises(ValueError):
            Pyro5.server.Daemon(nathost="bla", natport=5555, unixsocket="testsock")

    def testNATzeroPort(self):
        servertype = config.SERVERTYPE
        try:
            config.SERVERTYPE = "multiplex"
            with Pyro5.server.Daemon(nathost="nathosttest", natport=99999) as d:
                host, port = d.locationStr.split(":")
                assert port != 99999
                assert d.natLocationStr == "nathosttest:99999"
            with Pyro5.server.Daemon(nathost="nathosttest", natport=0) as d:
                host, port = d.locationStr.split(":")
                assert d.natLocationStr == "nathosttest:%s" % port
            config.SERVERTYPE = "thread"
            with Pyro5.server.Daemon(nathost="nathosttest", natport=99999) as d:
                host, port = d.locationStr.split(":")
                assert port != 99999
                assert d.natLocationStr == "nathosttest:99999"
            with Pyro5.server.Daemon(nathost="nathosttest", natport=0) as d:
                host, port = d.locationStr.split(":")
                assert d.natLocationStr == "nathosttest:%s" % port
        finally:
            config.SERVERTYPE = servertype

    def testNATconfig(self):
        try:
            config.NATHOST = None
            config.NATPORT = 0
            with Pyro5.server.Daemon() as d:
                assert d.natLocationStr is None
            config.NATHOST = "nathosttest"
            config.NATPORT = 12345
            with Pyro5.server.Daemon() as d:
                assert d.natLocationStr == "nathosttest:12345"
        finally:
            config.NATHOST = None
            config.NATPORT = 0

    def testBehaviorDefaults(self):
        class TestClass:
            pass
        with Pyro5.server.Daemon() as d:
            d.register(TestClass)
            instance_mode, instance_creator = TestClass._pyroInstancing
            assert instance_mode == "session"
            assert instance_creator is None

    def testInstanceCreationSingle(self):
        def creator(clazz):
            return clazz("testname")
        @Pyro5.server.behavior(instance_mode="single", instance_creator=creator)
        class TestClass:
            def __init__(self, name):
                self.name = name
        conn = Pyro5.socketutil.SocketConnection(socket.socket())
        d = Pyro5.server.Daemon()
        instance1 = d._getInstance(TestClass, conn)
        instance2 = d._getInstance(TestClass, conn)
        assert instance1.name == "testname"
        assert instance1 is instance2
        assert TestClass in d._pyroInstances
        assert instance1 is d._pyroInstances[TestClass]
        assert not(TestClass in conn.pyroInstances)

    def testBehaviorDefaultsIsSession(self):
        class ClassWithDefaults:
            def __init__(self):
                self.name = "yep"
        conn1 = Pyro5.socketutil.SocketConnection(socket.socket())
        conn2 = Pyro5.socketutil.SocketConnection(socket.socket())
        d = Pyro5.server.Daemon()
        d.register(ClassWithDefaults)
        instance1a = d._getInstance(ClassWithDefaults, conn1)
        instance1b = d._getInstance(ClassWithDefaults, conn1)
        instance2a = d._getInstance(ClassWithDefaults, conn2)
        instance2b = d._getInstance(ClassWithDefaults, conn2)
        assert instance1a is instance1b
        assert instance2a is instance2b
        assert instance1a is not instance2a
        assert not(ClassWithDefaults in d._pyroInstances)
        assert ClassWithDefaults in conn1.pyroInstances
        assert ClassWithDefaults in conn2.pyroInstances
        assert instance1a is conn1.pyroInstances[ClassWithDefaults]
        assert instance2a is conn2.pyroInstances[ClassWithDefaults]

    def testInstanceCreationSession(self):
        def creator(clazz):
            return clazz("testname")

        @Pyro5.server.behavior(instance_mode="session", instance_creator=creator)
        class ClassWithDecorator:
            def __init__(self, name):
                self.name = name
        conn1 = Pyro5.socketutil.SocketConnection(socket.socket())
        conn2 = Pyro5.socketutil.SocketConnection(socket.socket())
        d = Pyro5.server.Daemon()
        d.register(ClassWithDecorator)
        # check the class with the decorator first
        instance1a = d._getInstance(ClassWithDecorator, conn1)
        instance1b = d._getInstance(ClassWithDecorator, conn1)
        instance2a = d._getInstance(ClassWithDecorator, conn2)
        instance2b = d._getInstance(ClassWithDecorator, conn2)
        assert instance1a is instance1b
        assert instance2a is instance2b
        assert instance1a is not instance2a
        assert not(ClassWithDecorator in d._pyroInstances)
        assert ClassWithDecorator in conn1.pyroInstances
        assert ClassWithDecorator in conn2.pyroInstances
        assert instance1a is conn1.pyroInstances[ClassWithDecorator]
        assert instance2a is conn2.pyroInstances[ClassWithDecorator]


    def testInstanceCreationPerCall(self):
        def creator(clazz):
            return clazz("testname")
        @Pyro5.server.behavior(instance_mode="percall", instance_creator=creator)
        class TestClass:
            def __init__(self, name):
                self.name = name
        with Pyro5.socketutil.SocketConnection(socket.socket()) as conn:
            with Pyro5.server.Daemon() as d:
                instance1 = d._getInstance(TestClass, conn)
                instance2 = d._getInstance(TestClass, conn)
                assert instance1 is not instance2
                assert not(TestClass in d._pyroInstances)
                assert not(TestClass in conn.pyroInstances)

    def testInstanceCreationWrongType(self):
        def creator(clazz):
            return Pyro5.core.URI("PYRO:test@localhost:9999")
        @Pyro5.server.behavior(instance_creator=creator)
        class TestClass:
            def method(self):
                pass
        with Pyro5.socketutil.SocketConnection(socket.socket()) as conn:
            with Pyro5.server.Daemon() as d:
                with pytest.raises(TypeError):
                    d._getInstance(TestClass, conn)

    def testCombine(self):
        d1 = Pyro5.server.Daemon()
        d2 = Pyro5.server.Daemon()
        with pytest.raises(TypeError):
            d1.combine(d2)
        d1.close()
        d2.close()
        try:
            config.SERVERTYPE = "multiplex"
            d1 = Pyro5.server.Daemon()
            d2 = Pyro5.server.Daemon()
            nsuri, nsd, bcd = Pyro5.nameserver.start_ns(host="", bchost="")
            d1_selector = d1.transportServer.selector
            d1.combine(d2)
            d1.combine(nsd)
            d1.combine(bcd)
            assert d1_selector is d1.transportServer.selector
            assert d1_selector is d2.transportServer.selector
            assert d1_selector is nsd.transportServer.selector
            assert d1_selector is bcd.transportServer.selector
            assert len(d1.sockets) == 4
            assert d1.sock in d1.sockets
            assert d2.sock in d1.sockets
            assert nsd.sock in d1.sockets
            assert bcd in d1.sockets
            bcd.close()
            nsd.close()
            d2.close()
            d1.close()
        finally:
            config.SERVERTYPE = "thread"


class TestMetaInfo:
    def testMeta(self):
        with Pyro5.server.Daemon() as d:
            daemon_obj = d.objectsById[Pyro5.core.DAEMON_NAME]
            assert len(daemon_obj.info()) > 10
            meta = daemon_obj.get_metadata(Pyro5.core.DAEMON_NAME)
            assert meta["methods"] == {"get_metadata", "get_next_stream_item", "close_stream", "info", "ping", "registered"}

    def testMetaSerialization(self):
        with Pyro5.server.Daemon() as d:
            daemon_obj = d.objectsById[Pyro5.core.DAEMON_NAME]
            meta = daemon_obj.get_metadata(Pyro5.core.DAEMON_NAME)
            for ser_id in [Pyro5.serializers.JsonSerializer.serializer_id,
                           Pyro5.serializers.MarshalSerializer.serializer_id,
                           Pyro5.serializers.SerpentSerializer.serializer_id]:
                serializer = Pyro5.serializers.serializers_by_id[ser_id]
                data = serializer.dumps(meta)
                _ = serializer.loads(data)

    def testMetaResetCache(self):
        class Dummy:
            @Pyro5.server.expose
            def method(self):
                pass
        with Pyro5.server.Daemon() as d:
            dummy = Dummy()
            uri = d.register(dummy)
            daemon_obj = d.objectsById[Pyro5.core.DAEMON_NAME]
            meta = daemon_obj.get_metadata(uri.object)
            assert "newly_added_method" not in meta["methods"]
            assert "newly_added_method_two" not in meta["methods"]
            Dummy.newly_added_method = Pyro5.server.expose(lambda self: None)
            meta = daemon_obj.get_metadata(uri.object)
            assert "newly_added_method" not in meta["methods"]
            d.resetMetadataCache(uri.object)
            meta = daemon_obj.get_metadata(uri.object)
            assert "newly_added_method" in meta["methods"]
            Dummy.newly_added_method_two = Pyro5.server.expose(lambda self: None)
            d.resetMetadataCache(dummy)
            meta = daemon_obj.get_metadata(uri.object)
            assert "newly_added_method_two" in meta["methods"]
            del Dummy.newly_added_method
            del Dummy.newly_added_method_two
