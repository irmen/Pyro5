"""
The pyro wire protocol structures.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).


Wire messages contains of a fixed size header, an optional set of annotation chunks,
and then the payload data. This class doesn't deal with the payload data:
(de)serialization and handling of that data is done elsewhere.
Annotation chunks are only parsed.

The header format is::

    0x00   4s  4   'PYRO' (message identifier)
    0x04   H   2   protocol version
    0x06   B   1   message type
    0x07   B   1   serializer id
    0x08   H   2   message flags
    0x0a   H   2   sequence number   (to identify proper request-reply sequencing)
    0x0c   I   4   data length   (max 4 Gb)
    0x10   I   4   annotations length (max 4 Gb, total of all chunks, 0 if no annotation chunks present)
    0x14   16s 16  correlation uuid
    0x24   H   2   (reserved)
    0x26   H   2   magic number 0x4dc5
    total size: 0x28 (40 bytes)

After the header, zero or more annotation chunks may follow, of the format::

    4s  4   annotation id (4 ASCII letters)
    I   4   chunk length  (max 4 Gb)
    B   x   annotation chunk databytes

After that, the actual payload data bytes follow.
"""

import struct
import logging
import zlib
import uuid
from . import config, errors
from .callcontext import current_context


log = logging.getLogger("Pyro5.protocol")

MSG_CONNECT = 1
MSG_CONNECTOK = 2
MSG_CONNECTFAIL = 3
MSG_INVOKE = 4
MSG_RESULT = 5
MSG_PING = 6
FLAGS_EXCEPTION = 1 << 0
FLAGS_COMPRESSED = 1 << 1    # compress the data, but not the annotations (if you need that, do it yourself)
FLAGS_ONEWAY = 1 << 2
FLAGS_BATCH = 1 << 3
FLAGS_ITEMSTREAMRESULT = 1 << 4
FLAGS_KEEPSERIALIZED = 1 << 5
FLAGS_CORR_ID = 1 << 6

# wire protocol version. Note that if this gets updated, Pyrolite might need an update too.
PROTOCOL_VERSION = 502
_magic_number = 0x4dc5
_header_format = '!4sHBBHHII16sHH'
_header_size = struct.calcsize(_header_format)
_magic_number_bytes = _magic_number.to_bytes(2, "big")
_protocol_version_bytes = PROTOCOL_VERSION.to_bytes(2, "big")
_empty_correlation_id = b"\0" * 16


class SendingMessage:
    """Wire protocol message that will be sent."""

    def __init__(self, msgtype, flags, seq, serializer_id, payload, annotations=None):
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
        if current_context.correlation_id:
            flags |= FLAGS_CORR_ID
            self.corr_id = current_context.correlation_id.bytes
        else:
            self.corr_id = _empty_correlation_id
        header_data = struct.pack(_header_format, b"PYRO", PROTOCOL_VERSION, msgtype, serializer_id, flags, seq,
                                  len(payload), annotations_size, self.corr_id, 0, _magic_number)
        annotation_data = []
        for k, v in annotations.items():
            if len(k) != 4:
                raise errors.ProtocolError("annotation identifier must be 4 ascii characters")
            annotation_data.append(struct.pack("!4sI", k.encode("ascii"), len(v)))
            if not isinstance(v, (bytes, bytearray, memoryview)):
                raise errors.ProtocolError("annotation data must be bytes, bytearray, or memoryview", type(v))
            annotation_data.append(v)    # note: annotations are not compressed by Pyro
        self.data = header_data + b"".join(annotation_data) + payload

    def __repr__(self):
        return "<{:s}.{:s} at 0x{:x}; type={:d} flags={:d} seq={:d} size={:d}>" \
            .format(self.__module__, self.__class__.__name__, id(self), self.type, self.flags, self.seq, len(self.data))

    @staticmethod
    def ping(pyroConnection):
        """Convenience method to send a 'ping' message and wait for the 'pong' response"""
        ping = SendingMessage(MSG_PING, 0, 0, 42, b"ping")
        pyroConnection.send(ping.data)
        recv_stub(pyroConnection, [MSG_PING])


class ReceivingMessage:
    """Wire protocol message that was received."""
    def __init__(self, header, payload=None):
        """Parses a message from the given header."""
        tag, ver, self.type, self.serializer_id, self.flags, self.seq, self.data_size, \
            self.annotations_size, self.corr_id,  _, magic = struct.unpack(_header_format, header)
        if tag != b"PYRO" or ver != PROTOCOL_VERSION or magic != _magic_number:
            raise errors.ProtocolError("invalid message or protocol version")
        if self.data_size+self.annotations_size > config.MAX_MESSAGE_SIZE:
            raise errors.ProtocolError("message too large ({:d}, max={:d})"
                                       .format(self.data_size+self.annotations_size, config.MAX_MESSAGE_SIZE))
        self.data = None
        self.annotations = {}
        if payload is not None:
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
        if ld >= _header_size and data[38:40] != _magic_number_bytes:
            raise errors.ProtocolError("invalid magic number")

    def add_payload(self, payload):
        """Parses (annotations processing) and adds payload data to a received message."""
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
                self.annotations[annotation_id] = payload[i+8:i+8+length]     # note: it stores a memoryview!
                i += 8 + length
            assert i == self.annotations_size
            self.data = payload[self.annotations_size:]
        else:
            self.data = payload
        if self.flags & FLAGS_COMPRESSED:
            self.data = zlib.decompress(self.data)
            self.flags &= ~FLAGS_COMPRESSED
            self.data_size = len(self.data)


def log_wiredata(logger, text, msg):
    """logs all the given properties of the wire message in the given logger"""
    num_anns = len(msg.annotations) if hasattr(msg, "annotations") else 0
    corr_bytes = bytes(msg.corr_id) if hasattr(msg, "corr_id") else _empty_correlation_id
    corr_id = uuid.UUID(bytes=corr_bytes)
    logger.debug("%s: msgtype=%d flags=0x%x ser=%d seq=%d num_annotations=%s corr_id=%s\ndata=%r" %
                 (text, msg.type, msg.flags, msg.serializer_id, msg.seq, num_anns, corr_id, bytes(msg.data)))


def recv_stub(connection, accepted_msgtypes=None):
    """
    Receives a pyro message from a given connection.
    Accepts the given message types (None=any, or pass a sequence).
    Also reads annotation chunks and the actual payload data.
    """
    # TODO decouple i/o from actual protocol logic, so that the protocol can be easily unit tested
    header = connection.recv(6)  # 'PYRO' + 2 bytes protocol version
    ReceivingMessage.validate(header)
    header += connection.recv(_header_size - 6)
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
