"""
The pyro wire protocol message.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import hashlib
import struct
import logging
import sys
import zlib
from . import errors, constants
from .configuration import config


__all__ = ["Message"]

log = logging.getLogger("Pyro5.message")

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
FLAGS_META_ON_CONNECT = 1 << 4
FLAGS_ITEMSTREAMRESULT = 1 << 5
FLAGS_KEEPSERIALIZED = 1 << 6


class Message(object):
    """
    Pyro write protocol message.

    Wire messages contains of a fixed size header, an optional set of annotation chunks,
    and then the payload data. This class doesn't deal with the payload data:
    (de)serialization and handling of that data is done elsewhere.
    Annotation chunks are only parsed.

    The header format is::

       4   id ('PYRO')
       2   protocol version
       2   message type
       2   message flags
       2   sequence number
       4   data length   (i.e. 2 Gb data size limitation)
       2   data serialization format (serializer id)
       2   annotations length (total of all chunks, 0 if no annotation chunks present)
       2   (reserved)
       2   checksum

    After the header, zero or more annotation chunks may follow, of the format::

       4   id (ASCII)
       2   chunk length
       x   annotation chunk databytes

    After that, the actual payload data bytes follow.

    The sequencenumber is used to check if response messages correspond to the
    actual request message. This prevents the situation where Pyro would perhaps return
    the response data from another remote call (which would not result in an error otherwise!)
    This could happen for instance if the socket data stream gets out of sync, perhaps due To
    some form of signal that interrupts I/O.

    The header checksum is a simple sum of the header fields to make reasonably sure
    that we are dealing with an actual correct PYRO protocol header and not some random
    data that happens to start with the 'PYRO' protocol identifier.

    Pyro now uses one annotation chunk that you should not touch yourself:
    'CORR'  contains the correlation id (guid bytes)
    Other chunk names are free to use for custom purposes, but Pyro has the right
    to reserve more of them for internal use in the future.
    """
    __slots__ = ["type", "flags", "seq", "data", "data_size", "serializer_id", "annotations", "annotations_size"]
    header_format = '!4sHHHHiHHHH'
    header_size = struct.calcsize(header_format)
    checksum_magic = 0x34E9

    def __init__(self, msgType, databytes, serializer_id, flags, seq, annotations=None):
        self.type = msgType
        self.flags = flags
        self.seq = seq
        self.data = databytes
        self.data_size = len(self.data)
        self.serializer_id = serializer_id
        self.annotations = dict(annotations or {})
        self.annotations_size = sum([6 + len(v) for v in self.annotations.values()])
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
        if not (0 <= self.data_size <= 0x7fffffff):
            raise ValueError("invalid message size (outside range 0..2Gb)")
        checksum = (self.type + constants.PROTOCOL_VERSION + self.data_size + self.annotations_size +
                    self.serializer_id + self.flags + self.seq + self.checksum_magic) & 0xffff
        return struct.pack(self.header_format, b"PYRO", constants.PROTOCOL_VERSION, self.type, self.flags,
                           self.seq, self.data_size, self.serializer_id, self.annotations_size, 0, checksum)

    def __annotations_bytes(self):
        if self.annotations:
            a = []
            for k, v in self.annotations.items():
                if len(k) != 4:
                    raise errors.ProtocolError("annotation key must be of length 4")
                k = k.encode()
                a.append(struct.pack("!4sH", k, len(v)))
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
        if not headerData or len(headerData) != cls.header_size:
            raise errors.ProtocolError("header data size mismatch")
        tag, ver, msg_type, flags, seq, data_size, serializer_id, anns_size, _, checksum = struct.unpack(cls.header_format, headerData)
        if tag != b"PYRO" or ver != constants.PROTOCOL_VERSION:
            raise errors.ProtocolError("invalid data or unsupported protocol version")
        if checksum != (msg_type + ver + data_size + anns_size + flags + serializer_id + seq + cls.checksum_magic) & 0xffff:
            raise errors.ProtocolError("header checksum mismatch")
        msg = Message(msg_type, b"", serializer_id, flags, seq)
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
        msg = cls.from_header(connection.recv(cls.header_size))
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
                anno, length = struct.unpack("!4sH", annotations_data[i:i + 6])
                anno = anno.decode()
                msg.annotations[anno] = annotations_data[i + 6:i + 6 + length]
                if sys.platform == "cli":
                    msg.annotations[anno] = bytes(msg.annotations[anno])
                i += 6 + length
        # read data
        msg.data = connection.recv(msg.data_size)
        return msg

    @staticmethod
    def ping(pyroConnection):
        """Convenience method to send a 'ping' message and wait for the 'pong' response"""
        ping = Message(MSG_PING, b"ping", 42, 0, 0)
        pyroConnection.send(ping.to_bytes())
        Message.recv(pyroConnection, [MSG_PING])

    def decompress_if_needed(self):
        """Decompress the message data if it is compressed."""
        if self.flags & FLAGS_COMPRESSED:
            self.data = zlib.decompress(self.data)
            self.flags &= ~FLAGS_COMPRESSED
            self.data_size = len(self.data)
        return self
