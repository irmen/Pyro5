"""
Multi purpose stuff used by both clients and servers (URI etc)

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import re
import logging
import contextlib
import ipaddress
import socket
import random
import serpent
from typing import Union, Optional
from . import config, errors, socketutil, serializers


__all__ = ["URI", "DAEMON_NAME", "NAMESERVER_NAME", "resolve", "locate_ns", "type_meta"]

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
    uriRegEx = re.compile(r"(?P<protocol>[Pp][Yy][Rr][Oo][a-zA-Z]*):(?P<object>\S+?)(@(?P<location>.+))?$")

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

    def __str__(self):
        if self.protocol == "PYROMETA":
            result = "PYROMETA:" + ",".join(self.object)
        else:
            result = self.protocol + ":" + self.object
        if self.location:
            return result + "@" + self.location
        return result

    def __repr__(self):
        return "<%s.%s at 0x%x; %s>" % (self.__class__.__module__, self.__class__.__name__, id(self), str(self))

    def __eq__(self, other):
        if not isinstance(other, URI):
            return False
        return self.__getstate__() == other.__getstate__()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__getstate__())

    def __getstate__(self):
        return self.protocol, self.object, self.sockname, self.host, self.port

    def __setstate__(self, state):
        self.protocol, self.object, self.sockname, self.host, self.port = state


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


def resolve(uri: Union[str, URI], delay_time: float = 0.0) -> URI:
    """
    Resolve a 'magic' uri (PYRONAME, PYROMETA) into the direct PYRO uri.
    It finds a name server, and use that to resolve a PYRONAME uri into the direct PYRO uri pointing to the named object.
    If uri is already a PYRO uri, it is returned unmodified.
    You can consider this a shortcut function so that you don't have to locate and use a name server proxy yourself.
    Note: if you need to resolve more than a few names, consider using the name server directly instead of repeatedly
    calling this function, to avoid the name server lookup overhead from each call.
    You can set delay_time to the maximum number of seconds you are prepared to wait until a name registration
    becomes available in the nameserver.
    """
    if isinstance(uri, str):
        uri = URI(uri)
    elif not isinstance(uri, URI):
        raise TypeError("can only resolve Pyro URIs")
    if uri.protocol == "PYRO":
        return uri
    log.debug("resolving %s", uri)
    from . import nameserver   # doing it here to avoid circular import issues
    if uri.protocol == "PYRONAME":
        with locate_ns(uri.host, uri.port) as ns:
            return nameserver.lookup(ns, uri.object, delay_time)
    elif uri.protocol == "PYROMETA":
        with locate_ns(uri.host, uri.port) as ns:
            candidates = nameserver.yplookup(ns, uri.object, None, False, delay_time)
            if candidates:
                candidate = random.choice(list(candidates.values()))
                log.debug("resolved to candidate %s", candidate)
                return URI(candidate)
            raise errors.NamingError("no registrations available with desired metadata properties %s" % uri.object)
    else:
        raise errors.PyroError("invalid uri protocol")


def locate_ns(host: Union[str, ipaddress.IPv4Address, ipaddress.IPv6Address] = "",
              port: Optional[int] = None, broadcast: bool = True) -> "client.Proxy":
    """Get a proxy for a name server somewhere in the network."""
    from . import client
    if not host:
        # first try localhost if we have a good chance of finding it there
        if config.NS_HOST in ("localhost", "::1") or config.NS_HOST.startswith("127."):
            if ":" in config.NS_HOST:  # ipv6
                hosts = ["[%s]" % config.NS_HOST]
            else:
                # Some systems have 127.0.1.1 in the hosts file assigned to the hostname,
                # so try this too (only if it's actually used as a valid ip address)
                try:
                    socket.gethostbyaddr("127.0.1.1")
                    hosts = [config.NS_HOST] if config.NS_HOST == "127.0.1.1" else [config.NS_HOST, "127.0.1.1"]
                except socket.error:
                    hosts = [config.NS_HOST]
            for host in hosts:
                uristring = "PYRO:%s@%s:%d" % (NAMESERVER_NAME, host, port or config.NS_PORT)
                log.debug("locating the NS: %s", uristring)
                proxy = client.Proxy(uristring)
                with contextlib.suppress(errors.PyroError):
                    proxy._pyroBind()
                    log.debug("located NS")
                    return proxy
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
                    text = data.decode("iso-8859-1")
                    log.debug("located NS: %s", text)
                    proxy = client.Proxy(text)
                    return proxy
                except socket.timeout:
                    continue
            with contextlib.suppress(OSError, socket.error):
                sock.shutdown(socket.SHUT_RDWR)
            sock.close()
            log.debug("broadcast locate failed, try direct connection on NS_HOST")
        else:
            log.debug("skipping broadcast lookup")
        # broadcast failed or skipped, try PYRO directly on specific host
        host = config.NS_HOST
        port = config.NS_PORT
    elif not isinstance(host, str):
        host = str(host)    # take care of the occasion where host is an ipaddress.IpAddress
    # pyro direct lookup
    port = config.NS_PORT if not port else port
    if URI.isUnixsockLocation(host):
        uristring = "PYRO:%s@%s" % (NAMESERVER_NAME, host)
    else:
        # if not a unix socket, check for ipv6
        if host and ":" in str(host):
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
