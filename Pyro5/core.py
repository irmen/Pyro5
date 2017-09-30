"""
Multi purpose stuff used by both clients and servers (URI etc)

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import re
import logging
import threading
import socket
import random
import serpent
from . import config, errors, socketutil, serializers


__all__ = ["URI", "DAEMON_NAME", "NAMESERVER_NAME", "current_context", "resolve", "locate_ns", "type_meta"]

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
        return (self.protocol, self.object, self.sockname, self.host, self.port) ==\
               (other.protocol, other.object, other.sockname, other.host, other.port)

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
        return {
            "__class__": "Pyro5.core._ExceptionWrapper",
            "exception": serializers.SerializerBase.class_to_dict(self.exception)
        }


# register the special serializers for the pyro objects with Serpent
serpent.register_class(URI, serializers.pyro_class_serpent_serializer)
serpent.register_class(_ExceptionWrapper, serializers.pyro_class_serpent_serializer)
serializers.SerializerBase.register_class_to_dict(URI, serializers.serialize_pyro_object_to_dict, serpent_too=False)
serializers.SerializerBase.register_class_to_dict(_ExceptionWrapper, _ExceptionWrapper.__serialized_dict__, serpent_too=False)


def resolve(uri):
    """
    Resolve a 'magic' uri (PYRONAME, PYROMETA) into the direct PYRO uri.
    It finds a name server, and use that to resolve a PYRONAME uri into the direct PYRO uri pointing to the named object.
    If uri is already a PYRO uri, it is returned unmodified.
    You can consider this a shortcut function so that you don't have to locate and use a name server proxy yourself.
    Note: if you need to resolve more than a few names, consider using the name server directly instead of repeatedly
    calling this function, to avoid the name server lookup overhead from each call.
    """
    if isinstance(uri, str):
        uri = URI(uri)
    elif not isinstance(uri, URI):
        raise TypeError("can only resolve Pyro URIs")
    if uri.protocol == "PYRO":
        return uri
    log.debug("resolving %s", uri)
    if uri.protocol == "PYRONAME":
        with locate_ns(uri.host, uri.port) as nameserver:
            return nameserver.lookup(uri.object)
    elif uri.protocol == "PYROMETA":
        with locate_ns(uri.host, uri.port) as nameserver:
            candidates = nameserver.yplookup(meta_all=uri.object, return_metadata=False)
            if candidates:
                candidate = random.choice(list(candidates.values()))
                log.debug("resolved to candidate %s", candidate)
                return URI(candidate)
            raise errors.NamingError("no registrations available with desired metadata properties %s" % uri.object)
    else:
        raise errors.PyroError("invalid uri protocol")


def locate_ns(host=None, port=None, broadcast=True):
    """Get a proxy for a name server somewhere in the network."""
    from . import client  # XXX circular
    if host is None:
        # first try localhost if we have a good chance of finding it there
        if config.NS_HOST in ("localhost", "::1") or config.NS_HOST.startswith("127."):
            if ":" in config.NS_HOST:  # ipv6
                hosts = ["[%s]" % config.NS_HOST]
            else:
                # Some systems (Debian Linux) have 127.0.1.1 in the hosts file assigned to the hostname,
                # try this too for convenience sake (only if it's actually used as a valid ip address)
                try:
                    socket.gethostbyaddr("127.0.1.1")
                    hosts = [config.NS_HOST] if config.NS_HOST == "127.0.1.1" else [config.NS_HOST, "127.0.1.1"]
                except socket.error:
                    hosts = [config.NS_HOST]
            for host in hosts:
                uristring = "PYRO:%s@%s:%d" % (NAMESERVER_NAME, host, port or config.NS_PORT)
                log.debug("locating the NS: %s", uristring)
                proxy = client.Proxy(uristring)
                try:
                    proxy._pyroBind()
                    log.debug("located NS")
                    return proxy
                except errors.PyroError:
                    pass
        if config.PREFER_IP_VERSION == 6:
            broadcast = False   # ipv6 doesn't have broadcast. We should probably use multicast....
        if broadcast:
            # broadcast lookup
            if not port:
                port = config.NS_BCPORT
            log.debug("broadcast locate")
            sock = socketutil.create_bc_socket(reuseaddr=config.SOCK_REUSE, timeout=0.7)
            for _ in range(3):
                try:
                    for bcaddr in config.BROADCAST_ADDRS:
                        try:
                            sock.sendto(b"GET_NSURI", 0, (bcaddr, port))
                        except socket.error as x:
                            err = getattr(x, "errno", x.args[0])
                            # handle some errno's that some platforms like to throw:
                            if err not in socketutil.ERRNO_EADDRNOTAVAIL and err not in socketutil.ERRNO_EADDRINUSE:
                                raise
                    data, _ = sock.recvfrom(100)
                    sock.close()
                    data = data.decode("iso-8859-1")
                    log.debug("located NS: %s", data)
                    proxy = client.Proxy(data)
                    return proxy
                except socket.timeout:
                    continue
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except (OSError, socket.error):
                pass
            sock.close()
            log.debug("broadcast locate failed, try direct connection on NS_HOST")
        else:
            log.debug("skipping broadcast lookup")
        # broadcast failed or skipped, try PYRO directly on specific host
        host = config.NS_HOST
        port = config.NS_PORT
    # pyro direct lookup
    if not port:
        port = config.NS_PORT
    if URI.isUnixsockLocation(host):
        uristring = "PYRO:%s@%s" % (NAMESERVER_NAME, host)
    else:
        # if not a unix socket, check for ipv6
        if ":" in host:
            host = "[%s]" % host
        uristring = "PYRO:%s@%s:%d" % (NAMESERVER_NAME, host, port)
    uri = URI(uristring)
    log.debug("locating the NS: %s", uri)
    proxy = client.Proxy(uri)
    try:
        proxy._pyroBind()
        log.debug("located NS")
        return proxy
    except errors.PyroError as x:
        raise errors.NamingError("Failed to locate the nameserver") from x


def type_meta(class_or_object, prefix="class:"):
    """extracts type metadata from the given class or object, can be used as Name server metadata."""
    if hasattr(class_or_object, "__mro__"):
        return {prefix + c.__module__ + "." + c.__name__
                for c in class_or_object.__mro__ if c.__module__ not in ("builtins", "__builtin__")}
    if hasattr(class_or_object, "__class__"):
        return type_meta(class_or_object.__class__)
    return frozenset()


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
        self.response_annotations = {}
        self.correlation_id = None

    def to_global(self):
        return dict(self.__dict__)

    def from_global(self, values):
        self.client = values["client"]
        self.seq = values["seq"]
        self.msg_flags = values["msg_flags"]
        self.serializer_id = values["serializer_id"]
        self.annotations = values["annotations"]
        self.response_annotations = values["response_annotations"]
        self.correlation_id = values["correlation_id"]
        self.client_sock_addr = values["client_sock_addr"]

    def track_resource(self, resource):
        """keep a weak reference to the resource to be tracked for this connection"""
        if self.client:
            self.client.tracked_resources.add(resource)
        else:
            raise errors.PyroError("cannot track resource on a connectionless call")

    def untrack_resource(self, resource):
        """no longer track the resource for this connection"""
        if self.client:
            self.client.tracked_resources.discard(resource)
        else:
            raise errors.PyroError("cannot untrack resource on a connectionless call")


current_context = _CallContext()
"""the context object for the current call. (thread-local)"""
