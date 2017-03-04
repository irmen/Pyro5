import pytest
import Pyro5.serializers


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


class TestMarshalSerializer(TestSerpentSerializer):
    serializer = Pyro5.serializers.serializers["marshal"]


class TestJsonSerializer(TestSerpentSerializer):
    serializer = Pyro5.serializers.serializers["json"]


class TestMsgpackSerializer(TestSerpentSerializer):
    serializer = Pyro5.serializers.serializers["msgpack"]
