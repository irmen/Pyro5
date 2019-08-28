import array
import uuid
import contextlib
import Pyro5.serializers
from Pyro5.api import URI, Proxy, Daemon


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
        uri = URI("PYRO:obj@host:9999")
        ser = self.serializer.dumps(uri)
        uri2 = self.serializer.loads(ser)
        assert isinstance(uri2, URI)
        assert uri2 == uri
        proxy = Proxy("PYRO:obj@host:9999")
        proxy._pyroHandshake = "handshake"
        ser = self.serializer.dumps(proxy)
        proxy2 = self.serializer.loads(ser)
        assert isinstance(proxy2, Proxy)
        assert proxy2 == proxy
        assert proxy2._pyroHandshake == "handshake"
        with Daemon(host="localhost", port=12345, nathost="localhost", natport=9876) as daemon:
            ser = self.serializer.dumps(daemon)
            daemon2 = self.serializer.loads(ser)
            assert isinstance(daemon2, Daemon)

    def testSerializeDumpsAndDumpsCall(self):
        self.serializer.dumps(uuid.uuid4())
        self.serializer.dumps(URI("PYRO:test@test:4444"))
        self.serializer.dumps(Proxy("PYRONAME:foobar"))
        self.serializer.dumpsCall("obj", "method", (1, 2, 3), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, array.array('i', [1, 2, 3])), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, array.array('i', [1, 2, 3])), {"arg1": array.array('i', [1, 2, 3])})
        self.serializer.dumpsCall("obj", "method", (1, 2, URI("PYRO:test@test:4444")), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, URI("PYRO:test@test:4444")), {"arg1": URI("PYRO:test@test:4444")})
        self.serializer.dumpsCall("obj", "method", (1, 2, Proxy("PYRONAME:foobar")), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, Proxy("PYRONAME:foobar")), {"arg1": Proxy("PYRONAME:foobar")})

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


with contextlib.suppress(ImportError):
    import msgpack

    class TestMsgpackSerializer(TestSerpentSerializer):
        serializer = Pyro5.serializers.serializers["msgpack"]
