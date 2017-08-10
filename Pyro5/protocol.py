"""
The pyro wire protocol structures.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).


Wire messages contains of a fixed size header, an optional set of annotation chunks,
and then the payload data. This class doesn't deal with the payload data:
(de)serialization and handling of that data is done elsewhere.
Annotation chunks are only parsed.

The header format is::

   4s  4   'PYRO' (message identifier)
   H   2   protocol version
   B   1   message type
   B   1   serializer id
   H   2   message flags
   H   2   sequence number   (to identify proper request-reply sequencing)
   I   4   data length   (max 4 Gb)
   H   2   annotations length (total of all chunks, 0 if no annotation chunks present)
   H   2   (reserved)
   H   2   magic number 0x4dc5

After the header, zero or more annotation chunks may follow, of the format::

   4s  4   annotation id (4 ASCII letters)
   I   4   chunk length  (max 4 Gb)
   B   x   annotation chunk databytes

After that, the actual payload data bytes follow.
"""

# @todo put correlation ID in the header itself rather than as an annotation

import struct
import logging
import zlib
import uuid
from . import config, errors


__all__ = ["Message"]

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

# wire protocol version. Note that if this gets updated, Pyrolite might need an update too.
PROTOCOL_VERSION = 501
_magic_number = 0x4dc5
_header_format = '!4sHBBHHIHHH'
_header_size = struct.calcsize(_header_format)


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
            flags |= FLAGS_COMPRESSED       # @todo fix compression, serializer must not do it anymore
        self.flags = flags
        total_size = len(payload) + annotations_size
        if total_size > config.MAX_MESSAGE_SIZE:
            raise errors.ProtocolError("message too large ({:d}, max={:d})".format(total_size, config.MAX_MESSAGE_SIZE))
        header_data = struct.pack(_header_format, b"PYRO", PROTOCOL_VERSION, msgtype, serializer_id, flags, seq,
                                  len(payload), annotations_size, 0, _magic_number)
        annotation_data = []
        for k, v in annotations.items():
            if len(k) != 4:
                raise errors.ProtocolError("annotation identifier must be 4 ascii characters")
            annotation_data.append(struct.pack("!4sI", k.encode("ascii"), len(v)))
            if not isinstance(v, (bytes, bytearray)):
                raise errors.ProtocolError("annotation data must be bytes")
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
        MessageXXX.recv(pyroConnection, [MSG_PING])


class MessageXXX(object):  # @todo split up in SendingMessage and ReceivingMessage
    """Pyro write protocol message."""

    def __init__(self, msgType, databytes, serializer_id, flags, seq, annotations=None):
        self.type = msgType
        self.flags = flags
        self.seq = seq
        self.data = databytes
        self.data_size = len(self.data)
        self.serializer_id = serializer_id
        self.annotations = dict(annotations or {})
        self.annotations_size = sum([8 + len(v) for v in self.annotations.values()])
        if 0 < config.MAX_MESSAGE_SIZE < (self.data_size + self.annotations_size):
            raise errors.MessageTooLargeError("max message size exceeded (%d where max=%d)" %
                                              (self.data_size + self.annotations_size, config.MAX_MESSAGE_SIZE))

    def __repr__(self):
        return "<%s.%s at %x; type=%d flags=%d seq=%d datasize=%d #ann=%d>" %\
               (self.__module__, self.__class__.__name__, id(self), self.type, self.flags, self.seq, self.data_size, len(self.annotations))

    def to_bytes(self):
        """creates a byte stream containing the header followed by annotations (if any) followed by the data"""
        return self.__header_bytes() + self.__annotations_bytes() + self.data

    def __header_bytes(self):
        if self.data_size > 0x7fffffff:
            raise ValueError("invalid message size (outside range 0..2Gb)")
        return struct.pack(_header_format, b"PYRO", PROTOCOL_VERSION, self.type, self.serializer_id, self.flags,
                           self.seq, self.data_size, self.annotations_size, 0, _magic_number)

    def __annotations_bytes(self):
        if self.annotations:
            a = []
            for k, v in self.annotations.items():
                if len(k) != 4:
                    raise errors.ProtocolError("annotation key must be of length 4")
                k = k.encode()
                a.append(struct.pack("!4sI", k, len(v)))
                a.append(v)
            return b"".join(a)
        return b""

    # Note: this 'chunked' way of sending is not used because it triggers Nagle's algorithm
    # on some systems (linux). This causes big delays, unless you change the socket option
    # TCP_NODELAY to disable the algorithm. What also works, is sending all the message bytes
    # in one go: connection.send(message.to_bytes()). This is what Pyro does.
    def send(self, connection):
        """send the message as bytes over the connection"""
        connection.send(self.__header_bytes())
        if self.annotations:
            connection.send(self.__annotations_bytes())
        connection.send(self.data)

    @classmethod
    def from_header(cls, headerData):
        """Parses a message header. Does not yet process the annotations chunks and message data."""
        if not headerData or len(headerData) != _header_size:
            raise errors.ProtocolError("header data size mismatch")
        tag, ver, msg_type, serializer_id, flags, seq, data_size, anns_size, _, magic = struct.unpack(_header_format, headerData)
        if tag != b"PYRO" or ver != PROTOCOL_VERSION or magic != _magic_number:
            raise errors.ProtocolError("invalid message or unsupported protocol version")
        msg = MessageXXX(msg_type, b"", serializer_id, flags, seq)
        msg.data_size = data_size
        msg.annotations_size = anns_size
        return msg

    @classmethod
    def recv(cls, connection, requiredMsgTypes=None):
        """
        Receives a pyro message from a given connection.
        Accepts the given message types (None=any, or pass a sequence).
        Also reads annotation chunks and the actual payload data.
        """
        msg = cls.from_header(connection.recv(_header_size))
        if 0 < config.MAX_MESSAGE_SIZE < (msg.data_size + msg.annotations_size):
            errorMsg = "max message size exceeded (%d where max=%d)" % (msg.data_size + msg.annotations_size, config.MAX_MESSAGE_SIZE)
            log.error("connection " + str(connection) + ": " + errorMsg)
            connection.close()  # close the socket because at this point we can't return the correct seqnr for returning an errormsg
            exc = errors.MessageTooLargeError(errorMsg)
            exc.pyroMsg = msg
            raise exc
        if requiredMsgTypes and msg.type not in requiredMsgTypes:
            err = "invalid msg type %d received" % msg.type
            log.error(err)
            exc = errors.ProtocolError(err)
            exc.pyroMsg = msg
            raise exc
        if msg.annotations_size:
            # read annotation chunks
            annotations_data = connection.recv(msg.annotations_size)
            msg.annotations = {}
            i = 0
            while i < msg.annotations_size:
                anno, length = struct.unpack("!4sI", annotations_data[i:i + 8])
                anno = anno.decode()
                msg.annotations[anno] = annotations_data[i + 8:i + 8 + length]
                i += 8 + length
        # read data
        msg.data = connection.recv(msg.data_size)
        return msg

    def decompress_if_needed(self):
        """Decompress the message data if it is compressed."""
        if self.flags & FLAGS_COMPRESSED:
            self.data = zlib.decompress(self.data)
            self.flags &= ~FLAGS_COMPRESSED
            self.data_size = len(self.data)
        return self


def log_wiredata(logger, text, msg):
    """logs all the given properties of the wire message in the given logger"""
    if hasattr(msg, "annotations"):
        corr = str(uuid.UUID(bytes=msg.annotations["CORR"])) if "CORR" in msg.annotations else "?"
        logger.debug("%s: msgtype=%d flags=0x%x ser=%d seq=%d corr=%s\nannotations=%r\ndata=%r" %
                     (text, msg.type, msg.flags, msg.serializer_id, msg.seq, corr, msg.annotations, msg.data))
    else:
        logger.debug("%s: msgtype=%d flags=0x%x ser=%d seq=%d corr=?\ndata=%r" %
                     (text, msg.type, msg.flags, msg.serializer_id, msg.seq, msg.data))
        # @todo get corr from the header
