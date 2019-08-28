"""
Low level socket utilities.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import os
import platform
import socket
import errno
import time
import select
import ipaddress
import weakref
import contextlib
from typing import Union, Optional, Tuple, Dict, Type, Any
try:
    import ssl
except ImportError:
    pass
from . import config
from .errors import CommunicationError, TimeoutError, ConnectionClosedError


# Note: other interesting errnos are EPERM, ENOBUFS, EMFILE
# but it seems to me that all these signify an unrecoverable situation.
# So I didn't include them in the list of retryable errors.
ERRNO_RETRIES = [errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK, errno.EINPROGRESS]
if hasattr(errno, "WSAEINTR"):
    ERRNO_RETRIES.append(errno.WSAEINTR)
if hasattr(errno, "WSAEWOULDBLOCK"):
    ERRNO_RETRIES.append(errno.WSAEWOULDBLOCK)
if hasattr(errno, "WSAEINPROGRESS"):
    ERRNO_RETRIES.append(errno.WSAEINPROGRESS)

ERRNO_BADF = [errno.EBADF]
if hasattr(errno, "WSAEBADF"):
    ERRNO_BADF.append(errno.WSAEBADF)

ERRNO_ENOTSOCK = [errno.ENOTSOCK]
if hasattr(errno, "WSAENOTSOCK"):
    ERRNO_ENOTSOCK.append(errno.WSAENOTSOCK)
if not hasattr(socket, "SOL_TCP"):
    socket.SOL_TCP = socket.IPPROTO_TCP

ERRNO_EADDRNOTAVAIL = [errno.EADDRNOTAVAIL]
if hasattr(errno, "WSAEADDRNOTAVAIL"):
    ERRNO_EADDRNOTAVAIL.append(errno.WSAEADDRNOTAVAIL)

ERRNO_EADDRINUSE = [errno.EADDRINUSE]
if hasattr(errno, "WSAEADDRINUSE"):
    ERRNO_EADDRINUSE.append(errno.WSAEADDRINUSE)

# msg_waitall has proven to be unreliable on windows
USE_MSG_WAITALL = hasattr(socket, "MSG_WAITALL") and platform.system() != "Windows"


def get_ip_address(hostname: str, workaround127: bool = False, version: int = None) \
        -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
    """
    Returns the IP address for the given host. If you enable the workaround,
    it will use a little hack if the ip address is found to be the loopback address.
    The hack tries to discover an externally visible ip address instead (this only works for ipv4 addresses).
    Set ipVersion=6 to return ipv6 addresses, 4 to return ipv4, 0 to let OS choose the best one or None to use config.PREFER_IP_VERSION.
    """
    if not workaround127:
        with contextlib.suppress(ValueError):
            addr = ipaddress.ip_address(hostname)
            return addr

    def getaddr(ip_version):
        if ip_version == 6:
            family = socket.AF_INET6
        elif ip_version == 4:
            family = socket.AF_INET
        elif ip_version == 0:
            family = socket.AF_UNSPEC
        else:
            raise ValueError("unknown value for argument ipVersion.")
        ip = socket.getaddrinfo(hostname or socket.gethostname(), 80, family, socket.SOCK_STREAM, socket.SOL_TCP)[0][4][0]
        if workaround127 and (ip.startswith("127.") or ip == "0.0.0.0"):
            return get_interface("4.2.2.2").ip
        return ipaddress.ip_address(ip)

    try:
        if hostname and ':' in hostname and version is None:
            version = 0
        return getaddr(config.PREFER_IP_VERSION) if version is None else getaddr(version)
    except socket.gaierror:
        if version == 6 or (version is None and config.PREFER_IP_VERSION == 6):
            raise socket.error("unable to determine IPV6 address")
        return getaddr(0)


def get_interface(ip_address: Union[str, ipaddress.IPv4Address, ipaddress.IPv6Address]) \
        -> Union[ipaddress.IPv4Interface, ipaddress.IPv6Interface]:
    """tries to find the network interface that connects to the given host's address"""
    if isinstance(ip_address, str):
        ip_address = get_ip_address(ip_address)
    family = socket.AF_INET if ip_address.version == 4 else socket.AF_INET6
    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        sock.connect((str(ip_address), 53))  # 53=dns
        return ipaddress.ip_interface(sock.getsockname()[0])


def __retrydelays():
    # first try a few very short delays,
    # if that doesn't work, increase by 0.1 sec every time
    yield 0.0001
    yield 0.001
    yield 0.01
    d = 0.1
    while True:
        yield d
        d += 0.1


def receive_data(sock: socket.socket, size: int) -> bytes:
    """Retrieve a given number of bytes from a socket.
    It is expected the socket is able to supply that number of bytes.
    If it isn't, an exception is raised (you will not get a zero length result
    or a result that is smaller than what you asked for). The partial data that
    has been received however is stored in the 'partialData' attribute of
    the exception object."""
    try:
        delays = __retrydelays()
        msglen = 0
        data = bytearray()
        if USE_MSG_WAITALL and not hasattr(sock, "getpeercert"):    # ssl doesn't support recv flags
            while True:
                try:
                    chunk = sock.recv(size, socket.MSG_WAITALL)
                    if len(chunk) == size:
                        return chunk
                    # less data than asked, drop down into normal receive loop to finish
                    msglen = len(chunk)
                    data.extend(chunk)
                    break
                except socket.timeout:
                    raise TimeoutError("receiving: timeout")
                except socket.error as x:
                    err = getattr(x, "errno", x.args[0])
                    if err not in ERRNO_RETRIES:
                        raise ConnectionClosedError("receiving: connection lost: " + str(x))
                    time.sleep(next(delays))  # a slight delay to wait before retrying
        # old fashioned recv loop, we gather chunks until the message is complete
        while True:
            try:
                while msglen < size:
                    # 60k buffer limit avoids problems on certain OSes like VMS, Windows
                    chunk = sock.recv(min(60000, size - msglen))
                    if not chunk:
                        break
                    data.extend(chunk)
                    msglen += len(chunk)
                if len(data) != size:
                    err = ConnectionClosedError("receiving: not enough data")
                    err.partialData = data  # store the message that was received until now
                    raise err
                return data  # yay, complete
            except socket.timeout:
                raise TimeoutError("receiving: timeout")
            except socket.error as x:
                err = getattr(x, "errno", x.args[0])
                if err not in ERRNO_RETRIES:
                    raise ConnectionClosedError("receiving: connection lost: " + str(x))
                time.sleep(next(delays))  # a slight delay to wait before retrying
    except socket.timeout:
        raise TimeoutError("receiving: timeout")


def send_data(sock: socket.socket, data: bytes) -> None:
    """
    Send some data over a socket.
    Some systems have problems with ``sendall()`` when the socket is in non-blocking mode.
    For instance, Mac OS X seems to be happy to throw EAGAIN errors too often.
    This function falls back to using a regular send loop if needed.
    """
    if sock.gettimeout() is None:
        # socket is in blocking mode, we can use sendall normally.
        try:
            sock.sendall(data)
            return
        except socket.timeout:
            raise TimeoutError("sending: timeout")
        except socket.error as x:
            raise ConnectionClosedError("sending: connection lost: " + str(x))
    else:
        # Socket is in non-blocking mode, use regular send loop.
        delays = __retrydelays()
        while data:
            try:
                sent = sock.send(data)
                data = data[sent:]
            except socket.timeout:
                raise TimeoutError("sending: timeout")
            except socket.error as x:
                err = getattr(x, "errno", x.args[0])
                if err not in ERRNO_RETRIES:
                    raise ConnectionClosedError("sending: connection lost: " + str(x))
                time.sleep(next(delays))  # a slight delay to wait before retrying


def create_socket(bind: Union[Tuple, str] = None,
                  connect: Union[Tuple, str] = None,
                  reuseaddr: bool = False, keepalive: bool = True,
                  timeout: Optional[float] = -1, noinherit: bool = False,
                  ipv6: bool = False, nodelay: bool = True, sslContext: ssl.SSLContext = None) -> socket.socket:
    """
    Create a socket. Default socket options are keepalive and IPv4 family, and nodelay (nagle disabled).
    If 'bind' or 'connect' is a string, it is assumed a Unix domain socket is requested.
    Otherwise, a normal tcp/ip socket tuple (addr, port, ...) is used.
    Set ipv6=True to create an IPv6 socket rather than IPv4.
    Set ipv6=None to use the PREFER_IP_VERSION config setting.
    """
    if bind and connect:
        raise ValueError("bind and connect cannot both be specified at the same time")
    forceIPv6 = ipv6 or (ipv6 is None and config.PREFER_IP_VERSION == 6)
    if isinstance(bind, str) or isinstance(connect, str):
        family = socket.AF_UNIX
    elif not bind and not connect:
        family = socket.AF_INET6 if forceIPv6 else socket.AF_INET
    elif isinstance(bind, tuple):
        if not bind[0]:
            family = socket.AF_INET6 if forceIPv6 else socket.AF_INET
        else:
            addr = get_ip_address(bind[0])
            if addr.version == 4:
                if forceIPv6:
                    raise ValueError("IPv4 address is used bind argument with forceIPv6 argument:" + bind[0] + ".")
                family = socket.AF_INET
            elif addr.version == 6:
                family = socket.AF_INET6
                # replace bind addresses by their ipv6 counterparts (4-tuple)
                bind = (bind[0], bind[1], 0, 0)
            else:
                raise ValueError("unknown bind format.")
    elif isinstance(connect, tuple):
        if not connect[0]:
            family = socket.AF_INET6 if forceIPv6 else socket.AF_INET
        else:
            addr = get_ip_address(connect[0])
            if addr.version == 4:
                if forceIPv6:
                    raise ValueError("IPv4 address is used in connect argument with forceIPv6 argument:" + connect[0] + ".")
                family = socket.AF_INET
            elif addr.version == 6:
                family = socket.AF_INET6
                # replace connect addresses by their ipv6 counterparts (4-tuple)
                connect = (connect[0], connect[1], 0, 0)
            else:
                raise ValueError("unknown connect format.")
    else:
        raise ValueError("unknown bind or connect format.")
    sock = socket.socket(family, socket.SOCK_STREAM)
    if sslContext:
        if bind:
            sock = sslContext.wrap_socket(sock, server_side=True)
        elif connect:
            sock = sslContext.wrap_socket(sock, server_side=False, server_hostname=connect[0])
        else:
            sock = sslContext.wrap_socket(sock, server_side=False)
    if nodelay:
        set_nodelay(sock)
    if reuseaddr:
        set_reuseaddr(sock)
    if noinherit:
        set_noinherit(sock)
    if timeout is not None:
        if timeout == 0:
            timeout = None
        elif timeout >= 0:
            sock.settimeout(timeout)
    if bind:
        if type(bind) is tuple and bind[1] == 0:
            bind_unused_port(sock, bind[0])
        else:
            sock.bind(bind)
        with contextlib.suppress(OSError, IOError):
            sock.listen(100)
    if connect:
        try:
            sock.connect(connect)
        except socket.error as xv:
            # This can happen when the socket is in non-blocking mode (or has a timeout configured).
            # We check if it is a retryable errno (usually EINPROGRESS).
            # If so, we use select() to wait until the socket is in writable state,
            # essentially rebuilding a blocking connect() call.
            errno = getattr(xv, "errno", 0)
            if errno in ERRNO_RETRIES:
                if timeout:
                    if timeout < 0:
                        timeout = None
                    elif timeout < 0.1:
                        timeout = 0.1
                while True:
                    try:
                        sr, sw, se = select.select([], [sock], [sock], timeout)
                    except InterruptedError:
                        continue
                    if sock in sw:
                        break  # yay, writable now, connect() completed
                    elif sock in se:
                        sock.close()  # close the socket that refused to connect
                        raise socket.error("connect failed")
            else:
                sock.close()  # close the socket that refused to connect
                raise
    if keepalive:
        set_keepalive(sock)
    return sock


def create_bc_socket(bind: Union[Tuple, str] = None, reuseaddr: bool = False,
                     timeout: Optional[float] = -1, ipv6: bool = False) -> socket.socket:
    """
    Create a udp broadcast socket.
    Set ipv6=True to create an IPv6 socket rather than IPv4.
    Set ipv6=None to use the PREFER_IP_VERSION config setting.
    """
    forceIPv6 = ipv6 or (ipv6 is None and config.PREFER_IP_VERSION == 6)
    if not bind:
        family = socket.AF_INET6 if forceIPv6 else socket.AF_INET
    elif isinstance(bind, tuple):
        if not bind[0]:
            family = socket.AF_INET6 if forceIPv6 else socket.AF_INET
        else:
            addr = get_ip_address(bind[0])
            if addr.version == 4:
                if forceIPv6:
                    raise ValueError("IPv4 address is used with forceIPv6 option:" + bind[0] + ".")
                family = socket.AF_INET
            elif addr.version == 6:
                family = socket.AF_INET6
                bind = (bind[0], bind[1], 0, 0)
            else:
                raise ValueError("unknown bind format: %r" % (bind,))
    else:
        raise ValueError("unknown bind format: %r" % (bind,))
    sock = socket.socket(family, socket.SOCK_DGRAM)
    if family == socket.AF_INET:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if reuseaddr:
        set_reuseaddr(sock)
    if timeout is None:
        sock.settimeout(None)
    else:
        if timeout >= 0:
            sock.settimeout(timeout)
    if bind:
        host = bind[0] or ""
        port = bind[1]
        if port == 0:
            bind_unused_port(sock, host)
        else:
            if len(bind) == 2:
                sock.bind((host, port))  # ipv4
            elif len(bind) == 4:
                sock.bind((host, port, 0, 0))  # ipv6
            else:
                raise ValueError("bind must be None, 2-tuple or 4-tuple")
    return sock


def set_reuseaddr(sock: socket.socket) -> None:
    """sets the SO_REUSEADDR option on the socket, if possible."""
    with contextlib.suppress(Exception):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


def set_nodelay(sock: socket.socket) -> None:
    """sets the TCP_NODELAY option on the socket (to disable Nagle's algorithm), if possible."""
    with contextlib.suppress(Exception):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)


def set_keepalive(sock: socket.socket) -> None:
    """sets the SO_KEEPALIVE option on the socket, if possible."""
    with contextlib.suppress(Exception):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)


try:
    import fcntl

    def set_noinherit(sock: socket.socket) -> None:
        """Mark the given socket fd as non-inheritable to child processes"""
        fd = sock.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

except ImportError:
    # no fcntl available, try the windows version
    try:
        from ctypes import windll, WinError, wintypes
        # help ctypes to set the proper args for this kernel32 call on 64-bit pythons
        _SetHandleInformation = windll.kernel32.SetHandleInformation
        _SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
        _SetHandleInformation.restype = wintypes.BOOL  # don't need this, but might as well

        def set_noinherit(sock: socket.socket) -> None:
            """Mark the given socket fd as non-inheritable to child processes"""
            if not _SetHandleInformation(sock.fileno(), 1, 0):
                raise WinError()

    except (ImportError, NotImplementedError):
        # nothing available, define a dummy function
        def set_noinherit(sock: socket.socket) -> None:
            """Mark the given socket fd as non-inheritable to child processes (dummy)"""
            pass


class SocketConnection(object):
    """A wrapper class for plain sockets, containing various methods such as :meth:`send` and :meth:`recv`"""
    def __init__(self, sock: socket.socket, objectId: str = None, keep_open: bool = False) -> None:
        self.sock = sock
        self.objectId = objectId
        self.pyroInstances = {}    # type: Dict[Type, Any]   # pyro objects for instance_mode=session
        self.tracked_resources = weakref.WeakSet()   # type: weakref.WeakSet[Any]  # weakrefs to resources for this connection
        self.keep_open = keep_open

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def send(self, data: bytes) -> None:
        send_data(self.sock, data)

    def recv(self, size: int) -> bytes:
        return receive_data(self.sock, size)

    def close(self) -> None:
        if self.keep_open:
            return
        with contextlib.suppress(Exception):
            self.sock.shutdown(socket.SHUT_RDWR)
        with contextlib.suppress(Exception):
            self.sock.close()
        self.pyroInstances = {}   # release the session instances
        for rsc in self.tracked_resources:
            with contextlib.suppress(Exception):
                rsc.close()     # it is assumed a 'resource' has a close method.
        self.tracked_resources.clear()

    def fileno(self) -> int:
        return self.sock.fileno()

    def family(self) -> str:
        return family_str(self.sock)

    def settimeout(self, timeout: Optional[float]) -> None:
        self.sock.settimeout(timeout)

    def gettimeout(self) -> Optional[float]:
        return self.sock.gettimeout()

    def getpeercert(self) -> Optional[dict]:
        try:
            return self.sock.getpeercert()      # type: ignore
        except AttributeError:
            return None

    timeout = property(gettimeout, settimeout)


def family_str(sock) -> str:
    f = sock.family
    if f == socket.AF_INET:
        return "IPv4"
    if f == socket.AF_INET6:
        return "IPv6"
    if hasattr(socket, "AF_UNIX") and f == socket.AF_UNIX:
        return "Unix"
    return "???"


def find_probably_unused_port(family: int = socket.AF_INET, socktype: int = socket.SOCK_STREAM) -> int:
    """Returns an unused port that should be suitable for binding (likely, but not guaranteed).
    This code is copied from the stdlib's test.test_support module."""
    with socket.socket(family, socktype) as sock:
        return bind_unused_port(sock)


def bind_unused_port(sock: socket.socket, host: Union[str, ipaddress.IPv4Address, ipaddress.IPv6Address] = 'localhost') -> int:
    """Bind the socket to a free port and return the port number.
    This code is based on the code in the stdlib's test.test_support module."""
    if sock.family in (socket.AF_INET, socket.AF_INET6) and sock.type == socket.SOCK_STREAM:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            with contextlib.suppress(socket.error):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    if not isinstance(host, str):
        host = str(host)
    if sock.family == socket.AF_INET:
        if host == 'localhost':
            sock.bind(('127.0.0.1', 0))
        else:
            sock.bind((host, 0))
    elif sock.family == socket.AF_INET6:
        if host == 'localhost':
            sock.bind(('::1', 0, 0, 0))
        else:
            sock.bind((host, 0, 0, 0))
    else:
        raise CommunicationError("unsupported socket family: " + str(sock.family))
    return sock.getsockname()[1]


def interrupt_socket(address: Tuple[str, int]) -> None:
    """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
    with contextlib.suppress(socket.error):
        sock = create_socket(connect=address, keepalive=False, timeout=-1)
        with contextlib.suppress(socket.error, AttributeError):
            sock.sendall(b"!" * 16)
        with contextlib.suppress(OSError, socket.error):
            sock.shutdown(socket.SHUT_RDWR)
        sock.close()


__ssl_server_context = None
__ssl_client_context = None


def get_ssl_context(servercert: str = "", serverkey: str = "", clientcert: str = "", clientkey: str = "",
                    cacerts: str = "", keypassword: str = "") -> ssl.SSLContext:
    """creates an SSL context and caches it, so you have to set the parameters correctly before doing anything"""
    global __ssl_client_context, __ssl_server_context
    if servercert:
        if clientcert:
            raise ValueError("can't have both server cert and client cert")
        # server context
        if __ssl_server_context:
            return __ssl_server_context
        if not os.path.isfile(servercert):
            raise IOError("server cert file not found")
        if serverkey and not os.path.isfile(serverkey):
            raise IOError("server key file not found")
        __ssl_server_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        __ssl_server_context.load_cert_chain(servercert, serverkey or None, keypassword or None)    # type: ignore
        if cacerts:
            if os.path.isdir(cacerts):
                __ssl_server_context.load_verify_locations(capath=cacerts)
            else:
                __ssl_server_context.load_verify_locations(cafile=cacerts)
        if config.SSL_REQUIRECLIENTCERT:
            __ssl_server_context.verify_mode = ssl.CERT_REQUIRED   # 2-way ssl, server+client certs
        else:
            __ssl_server_context.verify_mode = ssl.CERT_NONE   # 1-way ssl, server cert only
        return __ssl_server_context
    else:
        # client context
        if __ssl_client_context:
            return __ssl_client_context
        __ssl_client_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        if clientcert:
            if not os.path.isfile(clientcert):
                raise IOError("client cert file not found")
            __ssl_client_context.load_cert_chain(clientcert, clientkey or None, keypassword or None)    # type: ignore
        if cacerts:
            if os.path.isdir(cacerts):
                __ssl_client_context.load_verify_locations(capath=cacerts)
            else:
                __ssl_client_context.load_verify_locations(cafile=cacerts)
        return __ssl_client_context
