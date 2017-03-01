import pytest
import Pyro5.protocol
import Pyro5.errors


class TestSendingMessage:
    def test_create(self):
        msg = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, 99, b"abcdefg")
        assert len(msg.data) > 1

    def test_compression(self):
        msg_uncompressed = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, 99, b"abcdefg"*100, compress=False)
        msg_compressed = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, 99, b"abcdefg"*100, compress=True)
        msg_notcompressed = Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 0, 42, 99, b"abcdefg", compress=True)
        assert not (msg_uncompressed.flags & Pyro5.protocol.FLAGS_COMPRESSED)
        assert not (msg_notcompressed.flags & Pyro5.protocol.FLAGS_COMPRESSED)
        assert msg_compressed.flags & Pyro5.protocol.FLAGS_COMPRESSED
        assert len(msg_uncompressed.data) > len(msg_compressed.data)


class TestReceivingMessage:
    def createmessage(self, compress=False):
        annotations = {
            "TEST": b"0123456789qwertyu",
            "UNIT": b"aaaaaaa"
        }
        return Pyro5.protocol.SendingMessage(Pyro5.protocol.MSG_INVOKE, 255, 42, 99, b"abcdefg"*100, annotations, compress=compress)

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
        msg.data[27] = 0xff   # kill the magic number
        with pytest.raises(Pyro5.errors.ProtocolError) as x:
            Pyro5.protocol.ReceivingMessage.validate(msg.data)
        assert "magic number" in str(x)
        msg.data[27] = 0xc1   # repair the magic number
        msg.data[5] = 0xff   # invalid protocol version
        with pytest.raises(Pyro5.errors.ProtocolError) as x:
            Pyro5.protocol.ReceivingMessage.validate(msg.data)
        assert "protocol version" in str(x)

    def test_create_nopayload(self):
        send_msg = self.createmessage(compress=True)
        header = send_msg.data[:Pyro5.protocol._header_size]
        msg = Pyro5.protocol.ReceivingMessage(header)
        assert msg.payload is None
        assert msg.type == Pyro5.protocol.MSG_INVOKE
        assert msg.flags == 255
        assert msg.seq == 42
        assert msg.serializer_id == 99
        assert len(msg.annotations) == 0

    def test_create_payload(self):
        send_msg = self.createmessage(compress=True)
        header = send_msg.data[:Pyro5.protocol._header_size]
        payload = send_msg.data[Pyro5.protocol._header_size:]
        msg = Pyro5.protocol.ReceivingMessage(header, payload)
        assert len(msg.payload) == 700
        assert msg.flags == 255 & ~Pyro5.protocol.FLAGS_COMPRESSED
        assert len(msg.annotations) == 2
        assert msg.annotations["TEST"] == b"0123456789qwertyu"
        assert msg.annotations["UNIT"] == b"aaaaaaa"
        assert type(msg.payload) is bytes

    def test_create_payload_memview(self):
        send_msg = self.createmessage()
        header = send_msg.data[:Pyro5.protocol._header_size]
        payload = send_msg.data[Pyro5.protocol._header_size:]
        msg = Pyro5.protocol.ReceivingMessage(header, payload)
        assert type(msg.payload) is memoryview
