"""
Socket server based on socket multiplexing. Doesn't use threads.
Uses the best available selector (kqueue, poll, select).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import socket
import time
import sys
import logging
import os
import selectors
import contextlib
from collections import defaultdict
from . import config, socketutil, errors

log = logging.getLogger("Pyro5.multiplexserver")


class SocketServer_Multiplex(object):
    """Multiplexed transport server for socket connections (uses select, poll, kqueue, ...)"""
    def __init__(self):
        """
        Init the socket.

        Args:
            self: (todo): write your description
        """
        self.sock = self.daemon = self.locationStr = None
        self.selector = selectors.DefaultSelector()
        self.shutting_down = False

    def init(self, daemon, host, port, unixsocket=None):
        """
        Initialize the connection.

        Args:
            self: (todo): write your description
            daemon: (todo): write your description
            host: (str): write your description
            port: (int): write your description
            unixsocket: (todo): write your description
        """
        log.info("starting multiplexed socketserver")
        log.debug("selector implementation: %s.%s", self.selector.__class__.__module__, self.selector.__class__.__name__)
        self.sock = None
        bind_location = unixsocket if unixsocket else (host, port)
        if config.SSL:
            sslContext = socketutil.get_ssl_context(servercert=config.SSL_SERVERCERT,
                                                    serverkey=config.SSL_SERVERKEY,
                                                    keypassword=config.SSL_SERVERKEYPASSWD,
                                                    cacerts=config.SSL_CACERTS)
            log.info("using SSL,  cert=%s  key=%s  cacerts=%s", config.SSL_SERVERCERT, config.SSL_SERVERKEY, config.SSL_CACERTS)
        else:
            sslContext = None
            log.info("not using SSL")
        self.sock = socketutil.create_socket(bind=bind_location,
                                             reuseaddr=config.SOCK_REUSE,
                                             timeout=config.COMMTIMEOUT,
                                             noinherit=True,
                                             nodelay=config.SOCK_NODELAY,
                                             sslContext=sslContext)
        self.daemon = daemon
        self._socketaddr = sockaddr = self.sock.getsockname()
        if not unixsocket and sockaddr[0].startswith("127."):
            if host is None or host.lower() != "localhost" and not host.startswith("127."):
                log.warning("weird DNS setup: %s resolves to localhost (127.x.x.x)", host)
        if unixsocket:
            self.locationStr = "./u:" + unixsocket
        else:
            host = host or sockaddr[0]
            port = port or sockaddr[1]
            if ":" in host:  # ipv6
                self.locationStr = "[%s]:%d" % (host, port)
            else:
                self.locationStr = "%s:%d" % (host, port)
        self.selector.register(self.sock, selectors.EVENT_READ, self)

    def __repr__(self):
        """
        Return a representation of this object.

        Args:
            self: (todo): write your description
        """
        return "<%s on %s; %d connections>" % (self.__class__.__name__, self.locationStr, len(self.selector.get_map()) - 1)

    def __del__(self):
        """
        Close the socket.

        Args:
            self: (todo): write your description
        """
        if self.sock is not None:
            self.selector.close()
            self.sock.close()
            self.sock = None

    def events(self, eventsockets):
        """handle events that occur on one of the sockets of this server"""
        for s in eventsockets:
            if self.shutting_down:
                return
            if s is self.sock:
                # server socket, means new connection
                conn = self._handleConnection(self.sock)
                if conn:
                    self.selector.register(conn, selectors.EVENT_READ, self)
            else:
                # must be client socket, means remote call
                active = self.handleRequest(s)
                if not active:
                    try:
                        self.daemon._clientDisconnect(s)
                    except Exception as x:
                        log.warning("Error in clientDisconnect: " + str(x))
                    self.selector.unregister(s)
                    s.close()
        self.daemon._housekeeping()

    def _handleConnection(self, sock):
        """
        Handle a socket.

        Args:
            self: (todo): write your description
            sock: (todo): write your description
        """
        try:
            if sock is None:
                return
            csock, caddr = sock.accept()
            if hasattr(csock, "getpeercert"):
                log.debug("connected %s - SSL", caddr)
            else:
                log.debug("connected %s - unencrypted", caddr)
            if config.COMMTIMEOUT:
                csock.settimeout(config.COMMTIMEOUT)
        except (socket.error, OSError) as x:
            err = getattr(x, "errno", x.args[0])
            if err in socketutil.ERRNO_BADF or err in socketutil.ERRNO_ENOTSOCK:
                # our server socket got destroyed
                raise errors.ConnectionClosedError("server socket closed")
            # socket errors may not lead to a server abort, so we log it and continue
            err = getattr(x, "errno", x.args[0])
            log.warning("accept() failed '%s' with errno=%d, shouldn't happen", x, err)
            return None
        try:
            conn = socketutil.SocketConnection(csock)
            if self.daemon._handshake(conn):
                return conn
            conn.close()
        except Exception:  # catch all errors, otherwise the event loop could terminate
            ex_t, ex_v, ex_tb = sys.exc_info()
            tb = errors.format_traceback(ex_t, ex_v, ex_tb)
            log.warning("error during connect/handshake: %s; %s", ex_v, "\n".join(tb))
            with contextlib.suppress(OSError, socket.error):
                csock.shutdown(socket.SHUT_RDWR)
            csock.close()
        return None

    def shutdown(self):
        """
        Shutdown the connection.

        Args:
            self: (todo): write your description
        """
        self.shutting_down = True
        self.wakeup()
        time.sleep(0.05)
        self.close()
        self.sock = None

    def close(self):
        """
        Close the socket.

        Args:
            self: (todo): write your description
        """
        self.selector.close()
        if self.sock:
            sockname = None
            with contextlib.suppress(OSError, socket.error):
                sockname = self.sock.getsockname()
            self.sock.close()
            if type(sockname) is str:
                # it was a Unix domain socket, remove it from the filesystem
                if os.path.exists(sockname):
                    os.remove(sockname)
        self.sock = None

    @property
    def sockets(self):
        """
        Return a list of : class :.

        Args:
            self: (todo): write your description
        """
        registrations = self.selector.get_map()
        if registrations:
            return [sk.fileobj for sk in registrations.values()]
        else:
            return []

    def wakeup(self):
        """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
        socketutil.interrupt_socket(self._socketaddr)

    def handleRequest(self, conn):
        """Handles a single connection request event and returns if the connection is still active"""
        try:
            self.daemon.handleRequest(conn)
            return True
        except (socket.error, errors.ConnectionClosedError, errors.SecurityError):
            # client went away or caused a security error.
            # close the connection silently.
            try:
                peername = conn.sock.getpeername()
                log.debug("disconnected %s", peername)
            except socket.error:
                log.debug("disconnected a client")
            return False
        except errors.TimeoutError as x:
            # for timeout errors we're not really interested in detailed traceback info
            log.warning("error during handleRequest: %s" % x)
            return False
        except Exception:
            # other error occurred, close the connection, but also log a warning
            ex_t, ex_v, ex_tb = sys.exc_info()
            tb = errors.format_traceback(ex_t, ex_v, ex_tb)
            msg = "error during handleRequest: %s; %s" % (ex_v, "".join(tb))
            log.warning(msg)
            return False

    def loop(self, loopCondition=lambda: True):
        """
        Main loop.

        Args:
            self: (todo): write your description
            loopCondition: (str): write your description
        """
        log.debug("entering multiplexed requestloop")
        while loopCondition():
            try:
                try:
                    events = self.selector.select(config.POLLTIMEOUT)
                except OSError:
                    events = []
                # get all the socket connection objects that have a READ event
                # (the WRITE events are ignored here, they're registered to let timeouts work etc)
                events_per_server = defaultdict(list)
                for key, mask in events:
                    if mask & selectors.EVENT_READ:
                        events_per_server[key.data].append(key.fileobj)
                for server, fileobjs in events_per_server.items():
                    server.events(fileobjs)
                if not events_per_server:
                    self.daemon._housekeeping()
            except socket.timeout:
                pass  # just continue the loop on a timeout
            except KeyboardInterrupt:
                log.debug("stopping on break signal")
                break

    def combine_loop(self, server):
        """
        Combine the server.

        Args:
            self: (todo): write your description
            server: (str): write your description
        """
        for sock in server.sockets:
            self.selector.register(sock, selectors.EVENT_READ, server)
        server.selector = self.selector
