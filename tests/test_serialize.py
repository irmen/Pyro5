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


class TestMarshalSerializer(TestSerpentSerializer):
    serializer = Pyro5.serializers.serializers["marshal"]


class TestJsonSerializer(TestSerpentSerializer):
    serializer = Pyro5.serializers.serializers["json"]


class TestMsgpackSerializer(TestSerpentSerializer):
    serializer = Pyro5.serializers.serializers["msgpack"]
