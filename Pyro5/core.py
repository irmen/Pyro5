"""
Multi purpose stuff used by both clients and servers (URI etc)

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""


import uuid
import re
import logging
import threading
import serpent
from . import errors, config, serializers

__all__ = ["URI", "DAEMON_NAME", "NAMESERVER_NAME"]

log = logging.getLogger("Pyro5.core")


# standard object name for the Daemon object
DAEMON_NAME = "Pyro.Daemon"

# standard name for the Name server itself
NAMESERVER_NAME = "Pyro.NameServer"


class URI(object):
    """
    Pyro object URI (universal resource identifier).
    The uri format is like this: ``PYRO:objectid@location`` where location is one of:

    - ``hostname:port`` (tcp/ip socket on given port)
    - ``./u:sockname`` (Unix domain socket on localhost)

    There is also a 'Magic format' for simple name resolution using Name server:
      ``PYRONAME:objectname[@location]``  (optional name server location, can also omit location port)
    And one that looks up things in the name server by metadata:
      ``PYROMETA:meta1,meta2,...[@location]``  (optional name server location, can also omit location port)

    You can write the protocol in lowercase if you like (``pyro:...``) but it will
    automatically be converted to uppercase internally.
    """
    uriRegEx = re.compile(r"(?P<protocol>[Pp][Yy][Rr][Oo][a-zA-Z]*):(?P<object>\S+?)(@(?P<location>\S+))?$")

    def __init__(self, uri):
        if isinstance(uri, URI):
            state = uri.__getstate__()
            self.__setstate__(state)
            return
        if not isinstance(uri, str):
            raise TypeError("uri parameter object is of wrong type")
        self.sockname = self.host = self.port = None
        match = self.uriRegEx.match(uri)
        if not match:
            raise errors.PyroError("invalid uri")
        self.protocol = match.group("protocol").upper()
        self.object = match.group("object")
        location = match.group("location")
        if self.protocol == "PYRONAME":
            self._parseLocation(location, config.NS_PORT)
        elif self.protocol == "PYRO":
            if not location:
                raise errors.PyroError("invalid uri")
            self._parseLocation(location, None)
        elif self.protocol == "PYROMETA":
            self.object = set(m.strip() for m in self.object.split(","))
            self._parseLocation(location, config.NS_PORT)
        else:
            raise errors.PyroError("invalid uri (protocol)")

    def _parseLocation(self, location, defaultPort):
        if not location:
            return
        if location.startswith("./u:"):
            self.sockname = location[4:]
            if (not self.sockname) or ':' in self.sockname:
                raise errors.PyroError("invalid uri (location)")
        else:
            if location.startswith("["):  # ipv6
                if location.startswith("[["):  # possible mistake: double-bracketing
                    raise errors.PyroError("invalid ipv6 address: enclosed in too many brackets")
                ipv6locationmatch = re.match(r"\[([0-9a-fA-F:%]+)](:(\d+))?", location)
                if not ipv6locationmatch:
                    raise errors.PyroError("invalid ipv6 address: the part between brackets must be a numeric ipv6 address")
                self.host, _, self.port = ipv6locationmatch.groups()
            else:
                self.host, _, self.port = location.partition(":")
            if not self.port:
                self.port = defaultPort
            try:
                self.port = int(self.port)
            except (ValueError, TypeError):
                raise errors.PyroError("invalid port in uri, port=" + str(self.port))

    @staticmethod
    def isUnixsockLocation(location):
        """determine if a location string is for a Unix domain socket"""
        return location.startswith("./u:")

    @property
    def location(self):
        """property containing the location string, for instance ``"servername.you.com:5555"``"""
        if self.host:
            if ":" in self.host:  # ipv6
                return "[%s]:%d" % (self.host, self.port)
            else:
                return "%s:%d" % (self.host, self.port)
        elif self.sockname:
            return "./u:" + self.sockname
        else:
            return None

    def asString(self):
        """the string representation of this object"""
        if self.protocol == "PYROMETA":
            result = "PYROMETA:" + ",".join(self.object)
        else:
            result = self.protocol + ":" + self.object
        location = self.location
        if location:
            result += "@" + location
        return result

    def __str__(self):
        return self.asString()

    def __repr__(self):
        return "<%s.%s at 0x%x; %s>" % (self.__class__.__module__, self.__class__.__name__, id(self), str(self))

    def __eq__(self, other):
        if not isinstance(other, URI):
            return False
        return (self.protocol, self.object, self.sockname, self.host, self.port) == (other.protocol, other.object, other.sockname, other.host, other.port)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.protocol, str(self.object), self.sockname, self.host, self.port))

    def __getstate__(self):
        return self.protocol, self.object, self.sockname, self.host, self.port

    def __setstate__(self, state):
        self.protocol, self.object, self.sockname, self.host, self.port = state

    def __getstate_for_dict__(self):
        return self.__getstate__()

    def __setstate_from_dict__(self, state):
        self.__setstate__(state)


class _ExceptionWrapper(object):
    """Class that wraps a remote exception. If this is returned, Pyro will
    re-throw the exception on the receiving side. Usually this is taken care of
    by a special response message flag, but in the case of batched calls this
    flag is useless and another mechanism was needed."""

    def __init__(self, exception):
        self.exception = exception

    def raiseIt(self):
        raise self.exception

    def __serialized_dict__(self):
        """serialized form as a dictionary"""
        from .serializers import SerializerBase
        return {
            "__class__": "Pyro5.core._ExceptionWrapper",
            "exception": SerializerBase.class_to_dict(self.exception)
        }


def log_wiredata(logger, text, msg):
    """logs all the given properties of the wire message in the given logger"""
    corr = str(uuid.UUID(bytes=msg.annotations["CORR"])) if "CORR" in msg.annotations else "?"
    logger.debug("%s: msgtype=%d flags=0x%x ser=%d seq=%d corr=%s\nannotations=%r\ndata=%r" %
                 (text, msg.type, msg.flags, msg.serializer_id, msg.seq, corr, msg.annotations, msg.data))


# call context thread local

class _CallContext(threading.local):
    def __init__(self):
        # per-thread initialization
        self.client = None
        self.client_sock_addr = None
        self.seq = 0
        self.msg_flags = 0
        self.serializer_id = 0
        self.annotations = {}
        self.correlation_id = None

    def to_global(self):
        return dict(self.__dict__)

    def from_global(self, values):
        self.client = values["client"]
        self.seq = values["seq"]
        self.msg_flags = values["msg_flags"]
        self.serializer_id = values["serializer_id"]
        self.annotations = values["annotations"]
        self.correlation_id = values["correlation_id"]
        self.client_sock_addr = values["client_sock_addr"]

current_context = _CallContext()
"""the context object for the current call. (thread-local)"""


# register the special serializers for the pyro objects
serpent.register_class(URI, serializers.pyro_class_serpent_serializer)
serpent.register_class(_ExceptionWrapper, serializers.pyro_class_serpent_serializer)
serializers.SerializerBase.register_class_to_dict(URI, serializers.serialize_pyro_object_to_dict, serpent_too=False)
serializers.SerializerBase.register_class_to_dict(_ExceptionWrapper, _ExceptionWrapper.__serialized_dict__, serpent_too=False)
