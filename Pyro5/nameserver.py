"""
Name Server and helper functions.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import logging
import random
import socket
from . import config, errors, core, client, socketutil, server

__all__ = ["resolve", "locateNS", "startNS"]

log = logging.getLogger("Pyro5.nameserver")


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
        uri = core.URI(uri)
    elif not isinstance(uri, core.URI):
        raise TypeError("can only resolve Pyro URIs")
    if uri.protocol == "PYRO":
        return uri
    log.debug("resolving %s", uri)
    if uri.protocol == "PYRONAME":
        with locateNS(uri.host, uri.port) as nameserver:
            return nameserver.lookup(uri.object)
    elif uri.protocol == "PYROMETA":
        with locateNS(uri.host, uri.port) as nameserver:
            candidates = nameserver.list(metadata_all=uri.object)
            if candidates:
                candidate = random.choice(list(candidates.values()))
                log.debug("resolved to candidate %s", candidate)
                return core.URI(candidate)
            raise errors.NamingError("no registrations available with desired metadata properties %s" % uri.object)
    else:
        raise errors.PyroError("invalid uri protocol")


def locateNS(host=None, port=None, broadcast=True):
    """Get a proxy for a name server somewhere in the network."""
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
                uristring = "PYRO:%s@%s:%d" % (core.NAMESERVER_NAME, host, port or config.NS_PORT)
                log.debug("locating the NS: %s", uristring)
                proxy = client.Proxy(uristring)
                try:
                    proxy._pyroBind()
                    log.debug("located NS")
                    return proxy
                except errors.PyroError:
                    pass
        if broadcast:
            # broadcast lookup
            if not port:
                port = config.NS_BCPORT
            log.debug("broadcast locate")
            sock = socketutil.createBroadcastSocket(reuseaddr=config.SOCK_REUSE, timeout=0.7)
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
    if core.URI.isUnixsockLocation(host):
        uristring = "PYRO:%s@%s" % (core.NAMESERVER_NAME, host)
    else:
        # if not a unix socket, check for ipv6
        if ":" in host:
            host = "[%s]" % host
        uristring = "PYRO:%s@%s:%d" % (core.NAMESERVER_NAME, host, port)
    uri = core.URI(uristring)
    log.debug("locating the NS: %s", uri)
    proxy = client.Proxy(uri)
    try:
        proxy._pyroBind()
        log.debug("located NS")
        return proxy
    except errors.PyroError as x:
        e = errors.NamingError("Failed to locate the nameserver")
        raise e from x


def startNS(hostname=None):
    uri = core.URI("PYRO:bla@host:5555")
    daemon = server.Daemon()
    bcserver = None
    return uri, daemon, bcserver   # XXX
