"""
The pyro wire protocol structures.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).


Wire messages contains of a fixed size header, an optional set of annotation chunks,
and then the payload data. It doesn't deal with the payload data itself;
(de)serialization and handling of that data is done elsewhere.

The header format is:

num_bytes   meaning
---------   -------
   4        'PYRO' (message identifier)
   2        protocol version
   2        message type
   2        message flags
   2        sequence number  (to identify proper request-reply sequencing)
   4        data length   (max 2 Gb)
   2        data serialization format (serializer id)
   4        annotations length (total of all chunks, 0 if no annotation chunks present)
   4        (reserved)
   4        magic number (message identifier)

After the header, zero or more annotation chunks may follow, of the format:

   4        annotation identifier (4 ascii letters)
   4        chunk length   (max 2 Gb)
   x        chunk data bytes

Finally the actual payload data bytes follow.
"""

import struct
import logging
import zlib
from . import errors, config


__all__ = ["SendingMessage", "ReceivingMessage"]

log = logging.getLogger("Pyro5.protocol")

MSG_CONNECT = 1
MSG_CONNECTOK = 2
MSG_CONNECTFAIL = 3
MSG_INVOKE = 4
MSG_RESULT = 5
MSG_PING = 6
FLAGS_EXCEPTION = 1 << 0
FLAGS_COMPRESSED = 1 << 1
FLAGS_ONEWAY = 1 << 2
FLAGS_BATCH = 1 << 3
FLAGS_ITEMSTREAMRESULT = 1 << 4

PROTOCOL_VERSION = 501


_header_format = "!4sHHHHiHiii"
_header_size = struct.calcsize(_header_format)
_magic_number = 0x04C11DB7
_magic_number_bytes = _magic_number.to_bytes(4, "big")
_protocol_version_bytes = PROTOCOL_VERSION.to_bytes(2, "big")


class SendingMessage:
    def __init__(self, msgtype, flags, seq, serializer_id, payload, annotations=None):
        """
        Creates a new wire protocol message to be sent.
        """
        self.type = msgtype
        self.seq = seq
        self.serializer_id = serializer_id
        annotations = annotations or {}
        annotations_size = sum([8 + len(v) for v in annotations.values()])
        flags &= ~FLAGS_COMPRESSED
        if config.COMPRESSION and len(payload) > 100:
            payload = zlib.compress(payload, 4)
            flags |= FLAGS_COMPRESSED
        self.flags = flags
        total_size = len(payload) + annotations_size
        if total_size > config.MAX_MESSAGE_SIZE:
            raise errors.ProtocolError("message too large ({:d}, max={:d})".format(total_size, config.MAX_MESSAGE_SIZE))
        header_data = struct.pack(_header_format, b"PYRO", PROTOCOL_VERSION, msgtype, flags, seq,
                                  len(payload), serializer_id, annotations_size, 0, _magic_number)
        annotation_data = []
        for k, v in annotations.items():
            if len(k) != 4:
                raise errors.ProtocolError("annotation identifier must be 4 ascii characters")
            annotation_data.append(struct.pack("!4si", k.encode("ascii"), len(v)))
            if not isinstance(v, (bytes, bytearray)):
                raise errors.ProtocolError("annotation data must be bytes")
            annotation_data.append(v)
        self.data = header_data + b"".join(annotation_data) + payload

    def __repr__(self):
        return "<{:s}.{:s} at 0x{:x}; type={:d} flags={:d} seq={:d} size={:d}>" \
            .format(self.__module__, self.__class__.__name__, id(self), self.type, self.flags, self.seq, len(self.data))


class ReceivingMessage:
    def __init__(self, header, payload=None):
        """Parses a message."""
        tag, ver, self.type, self.flags, self.seq, self.data_size, self.serializer_id, self.annotations_size, _, magic = struct.unpack(_header_format, header)
        if tag != b"PYRO" or ver != PROTOCOL_VERSION or magic != _magic_number:
            raise errors.ProtocolError("invalid message or protocol version")
        if self.data_size+self.annotations_size > config.MAX_MESSAGE_SIZE:
            raise errors.ProtocolError("message too large ({:d}, max={:d})".format(self.data_size+self.annotations_size, config.MAX_MESSAGE_SIZE))
        self.data = None
        self.annotations = {}
        if payload:
            self.add_payload(payload)

    def __repr__(self):
        return "<{:s}.{:s} at 0x{:x}; type={:d} flags={:d} seq={:d} size={:d}>" \
            .format(self.__module__, self.__class__.__name__, id(self), self.type, self.flags, self.seq, len(self.data or ""))

    @staticmethod
    def validate(data):
        """Checks if the message data looks like a valid Pyro message, if not, raise an error."""
        ld = len(data)
        if ld < 4:
            raise ValueError("data must be at least 4 bytes to be able to identify")
        if not data.startswith(b"PYRO"):
            raise errors.ProtocolError("invalid data")
        if ld >= 6 and data[4:6] != _protocol_version_bytes:
            raise errors.ProtocolError("invalid protocol version: {:d}".format(int.from_bytes(data[4:6], "big")))
        if ld >= _header_size and data[26:30] != _magic_number_bytes:
            raise errors.ProtocolError("invalid magic number")

    def add_payload(self, payload):
        """Parses and adds payload data to a received message."""
        assert not self.data
        if len(payload) != self.data_size + self.annotations_size:
            raise errors.ProtocolError("payload length doesn't match message header")
        if self.annotations_size:
            payload = memoryview(payload)  # avoid copying
            self.annotations = {}
            i = 0
            while i < self.annotations_size:
                annotation_id = bytes(payload[i:i+4]).decode("ascii")
                length = int.from_bytes(payload[i+4:i+8], "big")
                self.annotations[annotation_id] = payload[i+8:i+8+length]
                i += 8 + length
            assert i == self.annotations_size
            self.data = payload[self.annotations_size:]
        else:
            self.data = payload
        if self.flags & FLAGS_COMPRESSED:
            self.data = zlib.decompress(self.data)
            self.flags &= ~FLAGS_COMPRESSED
            self.data_size = len(self.data)


def recv_stub(connection, accepted_msgtypes=None):    # XXX
        """
        Receives a pyro message from a given connection.
        Accepts the given message types (None=any, or pass a sequence).
        Also reads annotation chunks and the actual payload data.
        """
        header = connection.recv(6)   # 'PYRO' + 2 bytes protocol version
        ReceivingMessage.validate(header)
        header += connection.recv(_header_size-6)
        msg = ReceivingMessage(header)
        if accepted_msgtypes and msg.type not in accepted_msgtypes:
            err = "invalid msg type {:d} received (expected: {:s})".format(msg.type, ",".join(str(t) for t in accepted_msgtypes))
            log.error(err)
            exc = errors.ProtocolError(err)
            exc.pyroMsg = msg
            raise exc
        payload = connection.recv(msg.annotations_size + msg.data_size)
        msg.add_payload(payload)
        return msg
