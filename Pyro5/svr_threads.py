"""
Socket server based on a worker thread pool. Doesn't use select.

Uses a single worker thread per client connection.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import socket
import logging
import sys
import time
import threading
import os
import selectors
import contextlib
from . import config, socketutil, errors

log = logging.getLogger("Pyro5.threadpoolserver")
_client_disconnect_lock = threading.Lock()


class ClientConnectionJob(object):
    """
    Takes care of a single client connection and all requests
    that may arrive during its life span.
    """

    def __init__(self, clientSocket, clientAddr, daemon):
        self.csock = socketutil.SocketConnection(clientSocket)
        self.caddr = clientAddr
        self.daemon = daemon

    def __call__(self):
        if self.handleConnection():
            try:
                while True:
                    try:
                        self.daemon.handleRequest(self.csock)
                    except (socket.error, errors.ConnectionClosedError):
                        # client went away.
                        log.debug("disconnected %s", self.caddr)
                        break
                    except errors.SecurityError:
                        log.debug("security error on client %s", self.caddr)
                        break
                    except errors.TimeoutError as x:
                        # for timeout errors we're not really interested in detailed traceback info
                        log.warning("error during handleRequest: %s" % x)
                        break
                    except Exception:
                        # other errors log a warning, break this loop and close the client connection
                        ex_t, ex_v, ex_tb = sys.exc_info()
                        tb = errors.format_traceback(ex_t, ex_v, ex_tb)
                        msg = "error during handleRequest: %s; %s" % (ex_v, "".join(tb))
                        log.warning(msg)
                        break
            finally:
                with _client_disconnect_lock:
                    try:
                        self.daemon._clientDisconnect(self.csock)
                    except Exception as x:
                        log.warning("Error in clientDisconnect: " + str(x))
                self.csock.close()

    def handleConnection(self):
        # connection handshake
        try:
            if self.daemon._handshake(self.csock):
                return True
            self.csock.close()
        except Exception:
            ex_t, ex_v, ex_tb = sys.exc_info()
            tb = errors.format_traceback(ex_t, ex_v, ex_tb)
            log.warning("error during connect/handshake: %s; %s", ex_v, "\n".join(tb))
            self.csock.close()
        return False

    def denyConnection(self, reason):
        log.warning("client connection was denied: " + reason)
        # return failed handshake
        self.daemon._handshake(self.csock, denied_reason=reason)
        self.csock.close()


class Housekeeper(threading.Thread):
    def __init__(self, daemon):
        super(Housekeeper, self).__init__(name="housekeeper")
        self.pyroDaemon = daemon
        self.stop = threading.Event()
        self.daemon = True
        self.waittime = min(config.POLLTIMEOUT or 0, max(config.COMMTIMEOUT or 0, 5))

    def run(self):
        while True:
            if self.stop.wait(self.waittime):
                break
            self.pyroDaemon._housekeeping()


class SocketServer_Threadpool(object):
    """transport server for socket connections, worker thread pool version."""

    def __init__(self):
        self.daemon = self.sock = self._socketaddr = self.locationStr = self.pool = None
        self.shutting_down = False
        self.housekeeper = None
        self._selector = selectors.DefaultSelector()

    def init(self, daemon, host, port, unixsocket=None):
        log.info("starting thread pool socketserver")
        self.daemon = daemon
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
        self._socketaddr = self.sock.getsockname()
        if not unixsocket and self._socketaddr[0].startswith("127."):
            if host is None or host.lower() != "localhost" and not host.startswith("127."):
                log.warning("weird DNS setup: %s resolves to localhost (127.x.x.x)", host)
        if unixsocket:
            self.locationStr = "./u:" + unixsocket
        else:
            host = host or self._socketaddr[0]
            port = port or self._socketaddr[1]
            if ":" in host:  # ipv6
                self.locationStr = "[%s]:%d" % (host, port)
            else:
                self.locationStr = "%s:%d" % (host, port)
        self.pool = Pool()
        self.housekeeper = Housekeeper(daemon)
        self.housekeeper.start()
        self._selector.register(self.sock, selectors.EVENT_READ, self)

    def __del__(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None
        if self.pool is not None:
            self.pool.close()
            self.pool = None
        if self.housekeeper:
            self.housekeeper.stop.set()
            self.housekeeper.join()
            self.housekeeper = None

    def __repr__(self):
        return "<%s on %s; %d workers>" % (self.__class__.__name__, self.locationStr, self.pool.num_workers())

    def loop(self, loopCondition=lambda: True):
        log.debug("threadpool server requestloop")
        while (self.sock is not None) and not self.shutting_down and loopCondition():
            try:
                self.events([self.sock])
            except (socket.error, OSError) as x:
                if not loopCondition():
                    # swallow the socket error if loop terminates anyway
                    # this can occur if we are asked to shutdown, socket can be invalid then
                    break
                # socket errors may not lead to a server abort, so we log it and continue
                err = getattr(x, "errno", x.args[0])
                log.warning("socket error '%s' with errno=%d, shouldn't happen", x, err)
                continue
            except KeyboardInterrupt:
                log.debug("stopping on break signal")
                break

    def combine_loop(self, server):
        raise TypeError("You can't use the loop combiner on the threadpool server type")

    def events(self, eventsockets):
        """used for external event loops: handle events that occur on one of the sockets of this server"""
        # we only react on events on our own server socket.
        # all other (client) sockets are owned by their individual threads.
        assert self.sock in eventsockets
        with contextlib.suppress(socket.timeout):   # just continue the loop on a timeout on accept
            events = self._selector.select(config.POLLTIMEOUT)
            if not events:
                return
            csock, caddr = self.sock.accept()
            if self.shutting_down:
                csock.close()
                return
            if hasattr(csock, "getpeercert"):
                log.debug("connected %s - SSL", caddr)
            else:
                log.debug("connected %s - unencrypted", caddr)
            if config.COMMTIMEOUT:
                csock.settimeout(config.COMMTIMEOUT)
            job = ClientConnectionJob(csock, caddr, self.daemon)
            try:
                self.pool.process(job)
            except NoFreeWorkersError:
                job.denyConnection("no free workers, increase server threadpool size")

    def shutdown(self):
        self.shutting_down = True
        self.wakeup()
        time.sleep(0.05)
        self.close()
        self.sock = None

    def close(self):
        if self.housekeeper:
            self.housekeeper.stop.set()
            self.housekeeper.join()
            self.housekeeper = None
        if self.sock:
            with contextlib.suppress(socket.error, OSError):
                sockname = self.sock.getsockname()
            with contextlib.suppress(Exception):
                self.sock.close()
                if type(sockname) is str:
                    # it was a Unix domain socket, remove it from the filesystem
                    if os.path.exists(sockname):
                        os.remove(sockname)
            self.sock = None
        self.pool.close()

    @property
    def sockets(self):
        # the server socket is all we care about, all client sockets are running in their own threads
        return [self.sock]

    @property
    def selector(self):
        raise TypeError("threadpool server doesn't have multiplexing selector")

    def wakeup(self):
        socketutil.interrupt_socket(self._socketaddr)


class PoolError(Exception):
    pass


class NoFreeWorkersError(PoolError):
    pass


class Worker(threading.Thread):
    def __init__(self, pool):
        super(Worker, self).__init__()
        self.daemon = True
        self.name = "Pyro-Worker-%d" % id(self)
        self.job_available = threading.Event()
        self.job = None
        self.pool = pool

    def process(self, job):
        self.job = job
        self.job_available.set()

    def run(self):
        while True:
            self.job_available.wait()
            self.job_available.clear()
            if self.job is None:
                break
            try:
                self.job()
            except Exception as x:
                log.exception("unhandled exception from job in worker thread %s: %s", self.name, x)
            self.job = None
            self.pool.notify_done(self)
        self.pool = None


class Pool(object):
    """
    A job processing pool that is using a pool of worker threads.
    The amount of worker threads in the pool is configurable and scales between min/max size.
    """
    def __init__(self):
        if config.THREADPOOL_SIZE < 1 or config.THREADPOOL_SIZE_MIN < 1:
            raise ValueError("threadpool sizes must be greater than zero")
        if config.THREADPOOL_SIZE_MIN > config.THREADPOOL_SIZE:
            raise ValueError("minimum threadpool size must be less than or equal to max size")
        self.idle = set()
        self.busy = set()
        self.closed = False
        for _ in range(config.THREADPOOL_SIZE_MIN):
            worker = Worker(self)
            self.idle.add(worker)
            worker.start()
        log.debug("worker pool created with initial size %d", self.num_workers())
        self.count_lock = threading.Lock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if not self.closed:
            log.debug("closing down")
            for w in list(self.busy):
                w.process(None)
            for w in list(self.idle):
                w.process(None)
            self.closed = True
            time.sleep(0.1)
            idle, self.idle = self.idle, set()
            busy, self.busy = self.busy, set()
            # check if the threads that are joined are not the current thread.
            current_thread = threading.current_thread()
            while idle:
                p = idle.pop()
                if p is not current_thread:
                    p.join(timeout=0.1)
            while busy:
                p = busy.pop()
                if p is not current_thread:
                    p.join(timeout=0.1)

    def __repr__(self):
        return "<%s.%s at 0x%x; %d busy workers; %d idle workers>" % \
               (self.__class__.__module__, self.__class__.__name__, id(self), len(self.busy), len(self.idle))

    def num_workers(self):
        return len(self.busy) + len(self.idle)

    def process(self, job):
        if self.closed:
            raise PoolError("job queue is closed")
        if self.idle:
            worker = self.idle.pop()
        elif self.num_workers() < config.THREADPOOL_SIZE:
            worker = Worker(self)
            worker.start()
        else:
            raise NoFreeWorkersError("no free workers available, increase thread pool size")
        self.busy.add(worker)
        worker.process(job)
        log.debug("worker counts: %d busy, %d idle", len(self.busy), len(self.idle))

    def notify_done(self, worker):
        if worker in self.busy:
            self.busy.remove(worker)
        if self.closed:
            worker.process(None)
            return
        if len(self.idle) >= config.THREADPOOL_SIZE_MIN:
            worker.process(None)
        else:
            self.idle.add(worker)
        log.debug("worker counts: %d busy, %d idle", len(self.busy), len(self.idle))
