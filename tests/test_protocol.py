import zlib
import pytest
import Pyro5.protocol
import Pyro5.errors
import Pyro5.protocol
import Pyro5.serializers
import Pyro5.errors
from Pyro5.protocol import SendingMessage, ReceivingMessage
from support import ConnectionMock


class TestSendingMessage:
    def test_create(self):
        msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, 99, b"abcdefg")
        assert len(msg.data) > 1

    def test_annotations_errors(self):
        with pytest.raises(Pyro5.errors.ProtocolError):
            Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, 99, b"abcdefg", annotations={"zxcv": "no_bytes"})
        with pytest.raises(Pyro5.errors.ProtocolError):
            Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, 99, b"abcdefg", annotations={"err": b"bytes"})

    def test_annotations(self):
        msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, 99, b"abcdefg", annotations={"zxcv": b"bytes"})
        assert len(msg.data) > 1

    def test_compression(self):
        compr_orig = Pyro5.config.COMPRESSION
        try:
            Pyro5.config.COMPRESSION = False
            msg_uncompressed = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, 99, b"abcdefg"*100)
            Pyro5.config.COMPRESSION = True
            msg_compressed = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, 99, b"abcdefg"*100)
            msg_notcompressed = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, 99, b"abcdefg")
            assert not (msg_uncompressed.flags & Pyro5.protocol.FLAGS_COMPRESSED)
            assert not (msg_notcompressed.flags & Pyro5.protocol.FLAGS_COMPRESSED)
            assert msg_compressed.flags & Pyro5.protocol.FLAGS_COMPRESSED
            assert len(msg_uncompressed.data) > len(msg_compressed.data)
        finally:
            Pyro5.config.COMPRESSION = compr_orig


class TestReceivingMessage:
    def createmessage(self, compression=False):
        compr_orig = Pyro5.config.COMPRESSION
        Pyro5.config.COMPRESSION = compression
        annotations = {
            "TEST": b"0123456789qwertyu",
            "UNIT": b"aaaaaaa"
        }
        msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 255, 42, 99, b"abcdefg"*100, annotations)
        Pyro5.config.COMPRESSION = compr_orig
        return msg

    def test_validate(self):
        with pytest.raises(ValueError):
            Pyro5.protocol.ReceivingMessage.validate(b"abc")
        with pytest.raises(Pyro5.errors.ProtocolError):
            Pyro5.protocol.ReceivingMessage.validate(b"ZXCV")
        Pyro5.protocol.ReceivingMessage.validate(b"PYRO")
        with pytest.raises(Pyro5.errors.ProtocolError):
            Pyro5.protocol.ReceivingMessage.validate(b"PYRO__")
        msg = self.createmessage()
        msg.data = bytearray(msg.data)
        Pyro5.protocol.ReceivingMessage.validate(msg.data)
        orig_magic = msg.data[38]
        msg.data[38] = 0xff   # kill the magic number
        with pytest.raises(Pyro5.errors.ProtocolError) as x:
            Pyro5.protocol.ReceivingMessage.validate(msg.data)
        assert "magic number" in str(x.value)
        msg.data[38] = orig_magic   # repair the magic number
        msg.data[5] = 0xff   # invalid protocol version
        with pytest.raises(Pyro5.errors.ProtocolError) as x:
            Pyro5.protocol.ReceivingMessage.validate(msg.data)
        assert "protocol version" in str(x.value)

    def test_create_nopayload(self):
        send_msg = self.createmessage(compression=True)
        header = send_msg.data[:Pyro5.protocol._header_size]
        msg = Pyro5.protocol.ReceivingMessage(header)
        assert msg.data is None
        assert msg.type == Pyro5.protocol.MSG_INVOKE
        assert msg.flags == 255
        assert msg.seq == 42
        assert msg.serializer_id == 99
        assert len(msg.annotations) == 0

    def test_create_payload(self):
        send_msg = self.createmessage(compression=True)
        header = send_msg.data[:Pyro5.protocol._header_size]
        payload = send_msg.data[Pyro5.protocol._header_size:]
        msg = Pyro5.protocol.ReceivingMessage(header, payload)
        assert len(msg.data) == 700
        assert msg.flags == 255 & ~Pyro5.protocol.FLAGS_COMPRESSED
        assert len(msg.annotations) == 2
        assert msg.annotations["TEST"] == b"0123456789qwertyu"
        assert msg.annotations["UNIT"] == b"aaaaaaa"
        assert type(msg.data) is bytes

    def test_create_payload_memview(self):
        send_msg = self.createmessage(compression=False)
        header = send_msg.data[:Pyro5.protocol._header_size]
        payload = send_msg.data[Pyro5.protocol._header_size:]
        msg = Pyro5.protocol.ReceivingMessage(header, payload)
        assert type(msg.data) is memoryview


class TestProtocolMessages:
    def testMessage(self):
        SendingMessage(99, 0, 0, Pyro5.serializers.SerpentSerializer.serializer_id, b"")  # doesn't check msg type here
        with pytest.raises(TypeError):
            ReceivingMessage("FOOBAR")
        with pytest.raises(Pyro5.errors.ProtocolError):
            ReceivingMessage(b"FOOBARFOOBARFOOBARFOOBARFOOBARFOOBAR1234")
        msg = SendingMessage(Pyro5.protocol.MSG_CONNECT, 0, 0, Pyro5.serializers.SerpentSerializer.serializer_id, b"hello")
        assert msg.type == Pyro5.protocol.MSG_CONNECT
        assert len(msg.data) == Pyro5.protocol._header_size + 5
        msg = ReceivingMessage(msg.data[:Pyro5.protocol._header_size], msg.data[Pyro5.protocol._header_size:])
        assert msg.type == Pyro5.protocol.MSG_CONNECT
        assert msg.data == b"hello"

        msg = SendingMessage(Pyro5.protocol.MSG_RESULT, 0, 0, Pyro5.serializers.SerpentSerializer.serializer_id, b"")
        msg = ReceivingMessage(msg.data[:Pyro5.protocol._header_size], msg.data[Pyro5.protocol._header_size:])
        assert msg.type == Pyro5.protocol.MSG_RESULT
        assert len(msg.data) == 0

        msg = SendingMessage(255, 0, 255, Pyro5.serializers.SerpentSerializer.serializer_id, b"").data
        assert len(msg) == 40
        msg = SendingMessage(1, 0, 255, Pyro5.serializers.SerpentSerializer.serializer_id, b"").data
        assert len(msg) == 40

        data = b"x" * 1000
        Pyro5.config.COMPRESSION = True
        msg = SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 0, Pyro5.serializers.SerpentSerializer.serializer_id, data).data
        assert len(msg) < len(data)
        Pyro5.config.COMPRESSION = False

    def testAnnotationsIdLength4(self):
        with pytest.raises(Pyro5.errors.ProtocolError):
            SendingMessage(Pyro5.protocol.MSG_CONNECT, 0, 0, Pyro5.serializers.SerpentSerializer.serializer_id, b"hello", {"TOOLONG": b"abcde"})
        with pytest.raises(Pyro5.errors.ProtocolError):
            SendingMessage(Pyro5.protocol.MSG_CONNECT, 0, 0, Pyro5.serializers.SerpentSerializer.serializer_id, b"hello", {"QQ": b"abcde"})

    def testRecvAnnotations(self):
        annotations = {"TEST": b"abcde"}
        msg = SendingMessage(Pyro5.protocol.MSG_CONNECT, 0, 0, Pyro5.serializers.SerpentSerializer.serializer_id, b"hello", annotations)
        c = ConnectionMock()
        c.send(msg.data)
        msg = Pyro5.protocol.recv_stub(c)
        assert len(c.received) == 0
        assert msg.data == b"hello"
        assert msg.annotations["TEST"] == b"abcde"

    def testCompression(self):
        data = b"The quick brown fox jumps over the lazy dog."*10
        compressed_data = zlib.compress(data)
        flags = Pyro5.protocol.FLAGS_COMPRESSED
        msg = SendingMessage(Pyro5.protocol.MSG_INVOKE, 42, flags, 1, compressed_data)
        assert msg.data != data
        assert len(msg.data) < len(data)

    def testRecvNoAnnotations(self):
        msg = SendingMessage(Pyro5.protocol.MSG_CONNECT, 42, 0, 0, b"hello")
        c = ConnectionMock()
        c.send(msg.data)
        msg = Pyro5.protocol.recv_stub(c)
        assert len(c.received) == 0
        assert msg.data_size == 5
        assert msg.data == b"hello"
        assert msg.annotations_size == 0
        assert len(msg.annotations) == 0
