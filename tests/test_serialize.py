"""
Tests for the data serializer.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""
import array
import collections
import copy
import math
import uuid
import pytest
import Pyro5.errors
import Pyro5.core
import Pyro5.client
import Pyro5.server
import Pyro5.serializers
from Pyro5 import config
from support import *


class TestSerpentSerializer:
    serializer = Pyro5.serializers.serializers["serpent"]

    def testSourceByteTypes(self):
        call_ser = self.serializer.dumpsCall("object", "method", [1, 2, 3], {"kwarg": 42})
        ser = self.serializer.dumps([4, 5, 6])
        _, _, vargs, _ = self.serializer.loadsCall(bytearray(call_ser))
        assert vargs == [1, 2, 3]
        d = self.serializer.loads(bytearray(ser))
        assert d == [4, 5, 6]
        _, _, vargs, _ = self.serializer.loadsCall(memoryview(call_ser))
        assert vargs == [1, 2, 3]
        d = self.serializer.loads(memoryview(ser))
        assert d == [4, 5, 6]

    def testSerializePyroTypes(self):
        uri = Pyro5.core.URI("PYRO:obj@host:9999")
        ser = self.serializer.dumps(uri)
        uri2 = self.serializer.loads(ser)
        assert isinstance(uri2, Pyro5.core.URI)
        assert uri2 == uri
        proxy = Pyro5.client.Proxy("PYRO:obj@host:9999")
        proxy._pyroHandshake = "handshake"
        ser = self.serializer.dumps(proxy)
        proxy2 = self.serializer.loads(ser)
        assert isinstance(proxy2, Pyro5.client.Proxy)
        assert proxy2 == proxy
        assert proxy2._pyroHandshake == "handshake"
        with Pyro5.server.Daemon(host="localhost", port=12345, nathost="localhost", natport=9876) as daemon:
            ser = self.serializer.dumps(daemon)
            daemon2 = self.serializer.loads(ser)
            assert isinstance(daemon2, Pyro5.server.Daemon)

    def testSerializeDumpsAndDumpsCall(self):
        self.serializer.dumps(uuid.uuid4())
        self.serializer.dumps(Pyro5.core.URI("PYRO:test@test:4444"))
        self.serializer.dumps(Pyro5.client.Proxy("PYRONAME:foobar"))
        self.serializer.dumpsCall("obj", "method", (1, 2, 3), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, array.array('i', [1, 2, 3])), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, array.array('i', [1, 2, 3])), {"arg1": array.array('i', [1, 2, 3])})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro5.core.URI("PYRO:test@test:4444")), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro5.core.URI("PYRO:test@test:4444")), {"arg1": Pyro5.core.URI("PYRO:test@test:4444")})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro5.client.Proxy("PYRONAME:foobar")), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro5.client.Proxy("PYRONAME:foobar")), {"arg1": Pyro5.client.Proxy("PYRONAME:foobar")})

    def testArrays(self):
        a1 = array.array('u', "hello")
        ser = self.serializer.dumps(a1)
        a2 = self.serializer.loads(ser)
        if type(a2) is array.array:
            assert a2 == a1
        else:
            assert a2 == "hello"
        a1 = array.array('h', [222, 333, 444, 555])
        ser = self.serializer.dumps(a1)
        a2 = self.serializer.loads(ser)
        if type(a2) is array.array:
            assert a2 == a1
        else:
            assert a2 == [222, 333, 444, 555]

    def testArrays2(self):
        a1 = array.array('u', "hello")
        ser = self.serializer.dumpsCall("obj", "method", [a1], {})
        a2 = self.serializer.loads(ser)
        a2 = a2["params"][0] if self.serializer.serializer_id == 3 else a2[2][0]      # 3=json serializer
        if type(a2) is array.array:
            assert a2 == a1
        else:
            assert a2 == "hello"
        a1 = array.array('h', [222, 333, 444, 555])
        ser = self.serializer.dumpsCall("obj", "method", [a1], {})
        a2 = self.serializer.loads(ser)
        a2 = a2["params"][0] if self.serializer.serializer_id == 3 else a2[2][0]      # 3=json serializer
        if type(a2) is array.array:
            assert a2 == a1
        else:
            assert a2 == [222, 333, 444, 555]


class TestMarshalSerializer(TestSerpentSerializer):
    serializer = Pyro5.serializers.serializers["marshal"]


class TestJsonSerializer(TestSerpentSerializer):
    serializer = Pyro5.serializers.serializers["json"]


if "msgpack" in Pyro5.serializers.serializers:
    class TestMsgpackSerializer(TestSerpentSerializer):
        serializer = Pyro5.serializers.serializers["msgpack"]


class TestSerializer2_serpent:
    SERIALIZER = "serpent"

    def setup_method(self):
        self.previous_serializer = config.SERIALIZER
        config.SERIALIZER = self.SERIALIZER
        self.serializer = Pyro5.serializers.serializers[config.SERIALIZER]

    def teardown_method(self):
        config.SERIALIZER = self.previous_serializer

    def testSerErrors(self):
        e1 = Pyro5.errors.NamingError("x")
        e1._pyroTraceback = ["this is the remote traceback"]
        orig_e = copy.copy(e1)
        e2 = Pyro5.errors.PyroError("x")
        e3 = Pyro5.errors.ProtocolError("x")
        p = self.serializer.dumps(e1)
        e = self.serializer.loads(p)
        assert isinstance(e, Pyro5.errors.NamingError)
        assert repr(e == repr(orig_e))
        assert e._pyroTraceback, "remote traceback info should be present" == ["this is the remote traceback"]
        p = self.serializer.dumps(e2)
        e = self.serializer.loads(p)
        assert isinstance(e, Pyro5.errors.PyroError)
        assert repr(e == repr(e2))
        p = self.serializer.dumps(e3)
        e = self.serializer.loads(p)
        assert isinstance(e, Pyro5.errors.ProtocolError)
        assert repr(e == repr(e3))

    def testSerializeExceptionWithAttr(self):
        ex = ZeroDivisionError("test error")
        ex._pyroTraceback = ["test traceback payload"]
        data = self.serializer.dumps(ex)
        ex2 = self.serializer.loads(data)
        assert type(ex2 == ZeroDivisionError)
        assert hasattr(ex2, "_pyroTraceback")
        assert ex2._pyroTraceback == ["test traceback payload"]

    def testSerCoreOffline(self):
        uri = Pyro5.core.URI("PYRO:9999@host.com:4444")
        p = self.serializer.dumps(uri)
        uri2 = self.serializer.loads(p)
        assert uri2 == uri
        assert uri2.protocol == "PYRO"
        assert uri2.object == "9999"
        assert uri2.location == "host.com:4444"
        assert uri2.port == 4444
        assert uri2.sockname is None

        uri = Pyro5.core.URI("PYRO:12345@./u:/tmp/socketname")
        p = self.serializer.dumps(uri)
        uri2 = self.serializer.loads(p)
        assert uri2 == uri
        assert uri2.protocol == "PYRO"
        assert uri2.object == "12345"
        assert uri2.location == "./u:/tmp/socketname"
        assert uri2.port is None
        assert uri2.sockname == "/tmp/socketname"

        proxy = Pyro5.client.Proxy("PYRO:9999@host.com:4444")
        proxy._pyroMaxRetries = 78
        assert not proxy._pyroConnection
        p = self.serializer.dumps(proxy)
        proxy2 = self.serializer.loads(p)
        assert not proxy._pyroConnection
        assert not proxy2._pyroConnection
        assert proxy._pyroUri == proxy2._pyroUri
        assert proxy2._pyroMaxRetries==0, "must be reset to defaults"

    def testNested(self):
        uri1 = Pyro5.core.URI("PYRO:1111@host.com:111")
        uri2 = Pyro5.core.URI("PYRO:2222@host.com:222")
        _ = self.serializer.dumps(uri1)
        data = [uri1, uri2]
        p = self.serializer.dumps(data)
        [u1, u2] = self.serializer.loads(p)
        assert u1 == uri1
        assert u2 == uri2

    def testSerDaemonHack(self):
        # This tests the hack that a Daemon should be serializable,
        # but only to support serializing Pyro objects.
        # The serialized form of a Daemon should be empty (and thus, useless)
        with Pyro5.server.Daemon(port=0) as daemon:
            d = self.serializer.dumps(daemon)
            d2 = self.serializer.loads(d)
            assert len(d2.__dict__) == 0, "deserialized daemon should be empty"
            assert "Pyro5.server.Daemon" in repr(d2)
            assert "unusable" in repr(d2)
            obj = MyThingFullExposed("hello")
            daemon.register(obj)
            _ = self.serializer.dumps(obj)

    def testPyroClasses(self):
        uri = Pyro5.core.URI("PYRO:object@host:4444")
        s = self.serializer.dumps(uri)
        x = self.serializer.loads(s)
        assert isinstance(x, Pyro5.core.URI)
        assert x == uri
        assert "URI" in repr(uri)
        assert str(uri == "PYRO:object@host:4444")
        uri = Pyro5.core.URI("PYRO:12345@./u:/tmp/socketname")
        s = self.serializer.dumps(uri)
        x = self.serializer.loads(s)
        assert isinstance(x, Pyro5.core.URI)
        assert x == uri
        proxy = Pyro5.client.Proxy(uri)
        proxy._pyroAttrs = set("abc")
        proxy._pyroMethods = set("def")
        proxy._pyroOneway = set("ghi")
        proxy._pyroHandshake = "apples"
        proxy._pyroMaxRetries = 78
        proxy._pyroSerializer = "serializer"
        s = self.serializer.dumps(proxy)
        x = self.serializer.loads(s)
        assert isinstance(x, Pyro5.client.Proxy)
        assert x._pyroUri == proxy._pyroUri
        assert x._pyroAttrs == set("abc")
        assert x._pyroMethods == set("def")
        assert x._pyroOneway == set("ghi")
        assert x._pyroHandshake == "apples"
        assert x._pyroSerializer == "serializer"
        assert x._pyroMaxRetries == 0, "must be reset to defaults"
        assert "Pyro5.client.Proxy" in repr(x)
        assert "Pyro5.client.Proxy" in str(x)
        daemon = Pyro5.server.Daemon()
        s = self.serializer.dumps(daemon)
        x = self.serializer.loads(s)
        assert isinstance(x, Pyro5.server.Daemon)
        assert "Pyro5.server.Daemon" in repr(x)
        assert "unusable" in repr(x)
        assert "Pyro5.server.Daemon" in str(x)
        assert "unusable" in str(x)
        wrapper = Pyro5.core._ExceptionWrapper(ZeroDivisionError("divided by zero"))
        s = self.serializer.dumps(wrapper)
        x = self.serializer.loads(s)
        assert isinstance(x, Pyro5.core._ExceptionWrapper)
        assert str(x.exception == "divided by zero")
        assert "ExceptionWrapper" in repr(x)
        assert "ExceptionWrapper" in str(x)

    def testProxySerializationCompat(self):
        proxy = Pyro5.client.Proxy("PYRO:object@host:4444")
        proxy._pyroSerializer = "serializer"
        pickle_state = proxy.__getstate__()
        assert len(pickle_state) == 6
        proxy.__setstate__(pickle_state)

    def testAutoProxyPartlyExposed(self):
        self.serializer.register_type_replacement(MyThingPartlyExposed, Pyro5.server._pyro_obj_to_auto_proxy)
        t1 = MyThingPartlyExposed("1")
        t2 = MyThingPartlyExposed("2")
        with Pyro5.server.Daemon() as d:
            d.register(t1, "thingy1")
            d.register(t2, "thingy2")
            data = [t1, ["apple", t2]]
            s = self.serializer.dumps(data)
            data = self.serializer.loads(s)
            assert data[1][0] == "apple"
            p1 = data[0]
            p2 = data[1][1]
            assert isinstance(p1, Pyro5.client.Proxy)
            assert isinstance(p2, Pyro5.client.Proxy)
            assert p1._pyroUri.object == "thingy1"
            assert p2._pyroUri.object == "thingy2"
            assert p1._pyroAttrs == {"readonly_prop1", "prop1"}
            assert p1._pyroMethods == {"exposed", "oneway"}
            assert p1._pyroOneway == {'oneway'}

    def testAutoProxyFullExposed(self):
        self.serializer.register_type_replacement(MyThingPartlyExposed, Pyro5.server._pyro_obj_to_auto_proxy)
        t1 = MyThingFullExposed("1")
        t2 = MyThingFullExposed("2")
        with Pyro5.server.Daemon() as d:
            d.register(t1, "thingy1")
            d.register(t2, "thingy2")
            data = [t1, ["apple", t2]]
            s = self.serializer.dumps(data)
            data = self.serializer.loads(s)
            assert data[1][0] == "apple"
            p1 = data[0]
            p2 = data[1][1]
            assert isinstance(p1, Pyro5.client.Proxy)
            assert isinstance(p2, Pyro5.client.Proxy)
            assert p1._pyroUri.object == "thingy1"
            assert p2._pyroUri.object == "thingy2"
            assert p1._pyroAttrs == {"prop1", "prop2", "readonly_prop1"}
            assert p1._pyroMethods == {'classmethod', 'method', 'oneway', 'staticmethod', 'exposed', "__dunder__"}
            assert p1._pyroOneway == {'oneway'}

    def testRegisterTypeReplacementSanity(self):
        self.serializer.register_type_replacement(int, lambda: None)
        with pytest.raises(ValueError):
            self.serializer.register_type_replacement(type, lambda: None)
        with pytest.raises(ValueError):
            self.serializer.register_type_replacement(42, lambda: None)

    def testCustomClassFail(self):
        o = MyThingFullExposed()
        s = self.serializer.dumps(o)
        with pytest.raises(Pyro5.errors.ProtocolError):
            _ = self.serializer.loads(s)

    def testCustomClassOk(self):
        o = MyThingPartlyExposed("test")
        Pyro5.serializers.SerializerBase.register_class_to_dict(MyThingPartlyExposed, mything_dict)
        Pyro5.serializers.SerializerBase.register_dict_to_class("CUSTOM-Mythingymabob", mything_creator)
        s = self.serializer.dumps(o)
        o2 = self.serializer.loads(s)
        assert isinstance(o2, MyThingPartlyExposed)
        assert o2.name == "test"
        # unregister the deserializer
        Pyro5.serializers.SerializerBase.unregister_dict_to_class("CUSTOM-Mythingymabob")
        with pytest.raises(Pyro5.errors.ProtocolError):
            self.serializer.loads(s)
        # unregister the serializer
        Pyro5.serializers.SerializerBase.unregister_class_to_dict(MyThingPartlyExposed)
        s = self.serializer.dumps(o)
        with pytest.raises(Pyro5.errors.SerializeError) as x:
            self.serializer.loads(s)
        msg = str(x.value)
        assert msg in ["unsupported serialized class: support.MyThingPartlyExposed",
                            "unsupported serialized class: PyroTests.support.MyThingPartlyExposed"]

    def testData(self):
        data = [42, "hello"]
        ser = self.serializer.dumps(data)
        data2 = self.serializer.loads(ser)
        assert data2 == data

    def testUnicodeData(self):
        data = "euro\u20aclowbytes\u0000\u0001\u007f\u0080\u00ff"
        ser = self.serializer.dumps(data)
        data2 = self.serializer.loads(ser)
        assert data2 == data

    def testUUID(self):
        data = uuid.uuid1()
        ser = self.serializer.dumps(data)
        data2 = self.serializer.loads(ser)
        uuid_as_str = str(data)
        assert data2==data or data2==uuid_as_str

    def testSet(self):
        data = {111, 222, 333}
        ser = self.serializer.dumps(data)
        data2 = self.serializer.loads(ser)
        assert data2 == data

    def testDeque(self):
        # serpent converts a deque into a primitive list
        deq = collections.deque([1, 2, 3, 4])
        ser = self.serializer.dumps(deq)
        data2 = self.serializer.loads(ser)
        assert data2 == [1, 2, 3, 4]

    def testCircularRefsValueError(self):
        with pytest.raises(ValueError):
            data = [42, "hello", Pyro5.client.Proxy("PYRO:dummy@dummy:4444")]
            data.append(data)
            ser = self.serializer.dumps(data)

    def testCallPlain(self):
        ser = self.serializer.dumpsCall("object", "method", ("vargs1", "vargs2"), {"kwargs": 999})
        obj, method, vargs, kwargs = self.serializer.loadsCall(ser)
        assert obj == "object"
        assert method == "method"
        assert len(vargs) == 2
        assert vargs[0] == "vargs1"
        assert vargs[1] == "vargs2"
        assert kwargs == {"kwargs": 999}

    def testCallPyroObjAsArg(self):
        uri = Pyro5.core.URI("PYRO:555@localhost:80")
        ser = self.serializer.dumpsCall("object", "method", [uri], {"thing": uri})
        obj, method, vargs, kwargs = self.serializer.loadsCall(ser)
        assert obj == "object"
        assert method == "method"
        assert vargs == [uri]
        assert kwargs == {"thing": uri}

    def testCallCustomObjAsArg(self):
        e = ZeroDivisionError("hello")
        ser = self.serializer.dumpsCall("object", "method", [e], {"thing": e})
        obj, method, vargs, kwargs = self.serializer.loadsCall(ser)
        assert obj == "object"
        assert method == "method"
        assert isinstance(vargs, list)
        assert isinstance(vargs[0], ZeroDivisionError)
        assert str(vargs[0] == "hello")
        assert isinstance(kwargs["thing"], ZeroDivisionError)
        assert str(kwargs["thing"] == "hello")

    def testSerializeException(self):
        e = ZeroDivisionError()
        d = self.serializer.dumps(e)
        e2 = self.serializer.loads(d)
        assert isinstance(e2, ZeroDivisionError)
        assert str(e2 == "")
        e = ZeroDivisionError("hello")
        d = self.serializer.dumps(e)
        e2 = self.serializer.loads(d)
        assert isinstance(e2, ZeroDivisionError)
        assert str(e2 == "hello")
        e = ZeroDivisionError("hello", 42)
        d = self.serializer.dumps(e)
        e2 = self.serializer.loads(d)
        assert isinstance(e2, ZeroDivisionError)
        assert str(e2) == "('hello', 42)"
        e.custom_attribute = 999
        ser = self.serializer.dumps(e)
        e2 = self.serializer.loads(ser)
        assert isinstance(e2, ZeroDivisionError)
        assert str(e2) == "('hello', 42)"
        assert e2.custom_attribute == 999

    def testSerializeSpecialException(self):
        assert "GeneratorExit" in Pyro5.serializers.all_exceptions
        e = GeneratorExit()
        d = self.serializer.dumps(e)
        e2 = self.serializer.loads(d)
        assert isinstance(e2, GeneratorExit)

    def testRecreateClasses(self):
        assert self.serializer.recreate_classes([1, 2, 3]) == [1, 2, 3]
        d = {"__class__": "invalid"}
        with pytest.raises(Pyro5.errors.ProtocolError):
            self.serializer.recreate_classes(d)
        d = {"__class__": "Pyro5.core.URI", "state": ['PYRO', '555', None, 'localhost', 80]}
        uri = self.serializer.recreate_classes(d)
        assert uri == Pyro5.core.URI("PYRO:555@localhost:80")
        number, uri = self.serializer.recreate_classes([1, {"uri": d}])
        assert number == 1
        assert uri["uri"] == Pyro5.core.URI("PYRO:555@localhost:80")

    def testUriSerializationWithoutSlots(self):
        u = Pyro5.core.URI("PYRO:obj@localhost:1234")
        d = self.serializer.dumps(u)
        u2 = self.serializer.loads(d)
        assert isinstance(u2, Pyro5.core.URI)
        assert str(u2) == "PYRO:obj@localhost:1234"

    def testFloatPrecision(self):
        f1 = 1482514078.54635912345
        f2 = 9876543212345.12345678987654321
        f3 = 11223344.556677889988776655e33
        floats = [f1, f2, f3]
        d = self.serializer.dumps(floats)
        v = self.serializer.loads(d)
        assert v, "float precision must not be compromised in any serializer" == floats

    def testSourceByteTypes_deserialize(self):
        call_ser = self.serializer.dumpsCall("object", "method", [1, 2, 3], {"kwarg": 42})
        ser = self.serializer.dumps([4, 5, 6])
        _, _, vargs, _ = self.serializer.loadsCall(bytearray(call_ser))
        assert vargs == [1, 2, 3]
        d = self.serializer.loads(bytearray(ser))
        assert d == [4, 5, 6]

    def testSourceByteTypes_deserialize_memoryview(self):
        call_ser = self.serializer.dumpsCall("object", "method", [1, 2, 3], {"kwarg": 42})
        ser = self.serializer.dumps([4, 5, 6])
        _, _, vargs, _ = self.serializer.loadsCall(memoryview(call_ser))
        assert vargs == [1, 2, 3]
        d = self.serializer.loads(memoryview(ser))
        assert d == [4, 5, 6]

    def testSourceByteTypes_loads(self):
        call_ser = self.serializer.dumpsCall("object", "method", [1, 2, 3], {"kwarg": 42})
        ser= self.serializer.dumps([4, 5, 6])
        _, _, vargs, _ = self.serializer.loadsCall(bytearray(call_ser))
        assert vargs == [1, 2, 3]
        d = self.serializer.loads(bytearray(ser))
        assert d == [4, 5, 6]

    def testSourceByteTypes_loads_memoryview(self):
        call_ser = self.serializer.dumpsCall("object", "method", [1, 2, 3], {"kwarg": 42})
        ser = self.serializer.dumps([4, 5, 6])
        _, _, vargs, _ = self.serializer.loadsCall(memoryview(call_ser))
        assert vargs == [1, 2, 3]
        d = self.serializer.loads(memoryview(ser))
        assert d == [4, 5, 6]

    def testSerializeDumpsAndDumpsCall(self):
        self.serializer.dumps(uuid.uuid4())
        self.serializer.dumps(Pyro5.core.URI("PYRO:test@test:4444"))
        self.serializer.dumps(Pyro5.client.Proxy("PYRONAME:foobar"))
        self.serializer.dumpsCall("obj", "method", (1, 2, 3), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, array.array('i', [1, 2, 3])), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, array.array('i', [1, 2, 3])), {"arg1": array.array('i', [1, 2, 3])})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro5.core.URI("PYRO:test@test:4444")), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro5.core.URI("PYRO:test@test:4444")), {"arg1": Pyro5.core.URI("PYRO:test@test:4444")})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro5.client.Proxy("PYRONAME:foobar")), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro5.client.Proxy("PYRONAME:foobar")), {"arg1": Pyro5.client.Proxy("PYRONAME:foobar")})

    def testArrays(self):
        a1 = array.array('u', "hello")
        ser = self.serializer.dumps(a1)
        a2 = self.serializer.loads(ser)
        if type(a2) is array.array:
            assert a2 == a1
        else:
            assert a2 == "hello"
        a1 = array.array('h', [222, 333, 444, 555])
        ser = self.serializer.dumps(a1)
        a2 = self.serializer.loads(ser)
        if type(a2) is array.array:
            assert a2 == a1
        else:
            assert a2 == [222, 333, 444, 555]

    def testArrays2(self):
        a1 = array.array('u', "hello")
        ser = self.serializer.dumpsCall("obj", "method", [a1], {})
        a2 = self.serializer.loads(ser)
        a2 = a2["params"][0] if self.SERIALIZER == "json" else a2[2][0]
        if type(a2) is array.array:
            assert a2 == a1
        else:
            assert a2 == "hello"
        a1 = array.array('h', [222, 333, 444, 555])
        ser = self.serializer.dumpsCall("obj", "method", [a1], {})
        a2 = self.serializer.loads(ser)
        a2 = a2["params"][0] if self.SERIALIZER == "json" else a2[2][0]
        if type(a2) is array.array:
            assert a2 == a1
        else:
            assert a2 == [222, 333, 444, 555]


class TestSerializer2_json(TestSerializer2_serpent):
    SERIALIZER = "json"

    def testSet(self):
        data = {111, 222, 333}
        ser = self.serializer.dumps(data)
        data2 = self.serializer.loads(ser)
        assert sorted(data2) == [111, 222, 333]

    def testDeque(self):
        pass    # can't serialize this in json


class TestSerializer2_marshal(TestSerializer2_serpent):
    SERIALIZER = "marshal"

    def testNested(self):
        pass    # marshall can't serialize custom objects

    def testAutoProxyPartlyExposed(self):
        pass    # marshall can't serialize custom objects

    def testAutoProxyFullExposed(self):
        pass    # marshall can't serialize custom objects

    def testRegisterTypeReplacementSanity(self):
        pass    # marshall doesn't support this feature at all

    def testDeque(self):
        pass    # marshall can't serialize custom objects


if "msgpack" in Pyro5.serializers.serializers:
    class TestSerializer2_msgpack(TestSerializer2_serpent):
        SERIALIZER = "msgpack"

        def testDeque(self):
            pass    # msgpack can't serialize this

        def testSet(self):
            data = {111, 222, 333}
            ser = self.serializer.dumps(data)
            data2 = self.serializer.loads(ser)
            assert sorted(data2) == [111, 222, 333]


class TestGenericCases:
    def testSerializersAvailable(self):
        _ = Pyro5.serializers.serializers["serpent"]
        _ = Pyro5.serializers.serializers["marshal"]
        _ = Pyro5.serializers.serializers["json"]

    def testAssignedSerializerIds(self):
        assert Pyro5.serializers.SerpentSerializer.serializer_id == 1
        assert Pyro5.serializers.MarshalSerializer.serializer_id == 2
        assert Pyro5.serializers.JsonSerializer.serializer_id == 3
        assert Pyro5.serializers.MsgpackSerializer.serializer_id == 4

    def testSerializersAvailableById(self):
        _ = Pyro5.serializers.serializers_by_id[1]  # serpent
        _ = Pyro5.serializers.serializers_by_id[2]  # marshal
        _ = Pyro5.serializers.serializers_by_id[3]  # json
        if "msgpack" in Pyro5.serializers.serializers:
            _ = Pyro5.serializers.serializers_by_id[4]  # msgpack
        assert 0 not in Pyro5.serializers.serializers_by_id
        assert 5 not in Pyro5.serializers.serializers_by_id

    def testDictClassFail(self):
        o = MyThingFullExposed("hello")
        d = Pyro5.serializers.SerializerBase.class_to_dict(o)
        assert d["name"] == "hello"
        assert d["__class__"] == "support.MyThingFullExposed"
        with pytest.raises(Pyro5.errors.ProtocolError):
            _ = Pyro5.serializers.SerializerBase.dict_to_class(d)

    def testDictException(self):
        x = ZeroDivisionError("hello", 42)
        expected = {
            "__class__": None,
            "__exception__": True,
            "args": ("hello", 42),
            "attributes": {}
        }
        expected["__class__"] = "builtins.ZeroDivisionError"
        d = Pyro5.serializers.SerializerBase.class_to_dict(x)
        assert d == expected
        x.custom_attribute = 999
        expected["attributes"] = {"custom_attribute": 999}
        d = Pyro5.serializers.SerializerBase.class_to_dict(x)
        assert d == expected

    def testDictClassOk(self):
        uri = Pyro5.core.URI("PYRO:object@host:4444")
        d = Pyro5.serializers.SerializerBase.class_to_dict(uri)
        assert d["__class__"] == "Pyro5.core.URI"
        assert "state" in d
        x = Pyro5.serializers.SerializerBase.dict_to_class(d)
        assert isinstance(x, Pyro5.core.URI)
        assert x == uri
        assert x.port == 4444
        uri = Pyro5.core.URI("PYRO:12345@./u:/tmp/socketname")
        d = Pyro5.serializers.SerializerBase.class_to_dict(uri)
        assert d["__class__"] == "Pyro5.core.URI"
        assert "state" in d
        x = Pyro5.serializers.SerializerBase.dict_to_class(d)
        assert isinstance(x, Pyro5.core.URI)
        assert x == uri
        assert x.sockname == "/tmp/socketname"

    def testCustomDictClass(self):
        o = MyThingPartlyExposed("test")
        Pyro5.serializers.SerializerBase.register_class_to_dict(MyThingPartlyExposed, mything_dict)
        Pyro5.serializers.SerializerBase.register_dict_to_class("CUSTOM-Mythingymabob", mything_creator)
        d = Pyro5.serializers.SerializerBase.class_to_dict(o)
        assert d["__class__"] == "CUSTOM-Mythingymabob"
        assert d["name"] == "test"
        x = Pyro5.serializers.SerializerBase.dict_to_class(d)
        assert isinstance(x, MyThingPartlyExposed)
        assert x.name == "test"
        # unregister the conversion functions and try again
        Pyro5.serializers.SerializerBase.unregister_class_to_dict(MyThingPartlyExposed)
        Pyro5.serializers.SerializerBase.unregister_dict_to_class("CUSTOM-Mythingymabob")
        d_orig = Pyro5.serializers.SerializerBase.class_to_dict(o)
        clsname = d_orig["__class__"]
        assert clsname.endswith("support.MyThingPartlyExposed")
        with pytest.raises(Pyro5.errors.ProtocolError):
            _ = Pyro5.serializers.SerializerBase.dict_to_class(d)

    def testExceptionNamespace(self):
        data = {'__class__': 'builtins.ZeroDivisionError',
                '__exception__': True,
                'args': ('hello', 42),
                'attributes': {"test_attribute": 99}}
        exc = Pyro5.serializers.SerializerBase.dict_to_class(data)
        assert isinstance(exc, ZeroDivisionError)
        assert repr(exc) == "ZeroDivisionError('hello', 42)"
        assert exc.test_attribute == 99

    def testExceptionNotTagged(self):
        data = {'__class__': 'builtins.ZeroDivisionError',
                'args': ('hello', 42),
                'attributes': {}}
        with pytest.raises(Pyro5.errors.SerializeError) as cm:
            _ = Pyro5.serializers.SerializerBase.dict_to_class(data)
        assert str(cm.value) == "unsupported serialized class: builtins.ZeroDivisionError"

    def testWeirdFloats(self):
        ser = Pyro5.serializers.serializers[config.SERIALIZER]
        p = ser.dumps([float("+inf"), float("-inf"), float("nan")])
        s2 = ser.loads(p)
        assert math.isinf(s2[0])
        assert math.copysign(1, s2[0]) == 1.0
        assert math.isinf(s2[1])
        assert math.copysign(1, s2[1]) == -1.0
        assert math.isnan(s2[2])


def mything_dict(obj):
    return {
        "__class__": "CUSTOM-Mythingymabob",
        "name": obj.name
    }


def mything_creator(classname, d):
    assert classname == "CUSTOM-Mythingymabob"
    assert d["__class__"] == "CUSTOM-Mythingymabob"
    return MyThingPartlyExposed(d["name"])

