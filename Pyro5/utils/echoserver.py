"""
Echo server for test purposes.
This is usually invoked by starting this module as a script:

  :command:`python -m Pyro5.test.echoserver`
  or simply: :command:`pyro5-test-echoserver`


It is also possible to use the :class:`EchoServer` in user code
but that is not terribly useful.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys
import time
import threading
from argparse import ArgumentParser
from .. import config, core, server, nameserver


__all__ = ["EchoServer"]


@server.expose
class EchoServer(object):
    """
    The echo server object that is provided as a Pyro object by this module.
    If its :attr:`verbose` attribute is set to ``True``, it will print messages as it receives calls.
    """
    _verbose = False
    _must_shutdown = False

    def echo(self, message):
        """return the message"""
        if self._verbose:
            message_str = repr(message).encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding)
            print("%s - echo: %s" % (time.asctime(), message_str))
        return message

    def error(self):
        """generates a simple exception without text"""
        if self._verbose:
            print("%s - error: generating exception" % time.asctime())
        raise ValueError("this is the generated error from echoserver echo() method")

    def error_with_text(self):
        """generates a simple exception with message"""
        if self._verbose:
            print("%s - error: generating exception" % time.asctime())
        raise ValueError("the message of the error")

    @server.oneway
    def oneway_echo(self, message):
        """just like echo, but oneway; the client won't wait for response"""
        if self._verbose:
            message_str = repr(message).encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding)
            print("%s - oneway_echo: %s" % (time.asctime(), message_str))
        return "bogus return value"

    def slow(self):
        """returns (and prints) a message after a certain delay"""
        if self._verbose:
            print("%s - slow: waiting a bit..." % time.asctime())
        time.sleep(5)
        if self._verbose:
            print("%s - slow: returning result" % time.asctime())
        return "Finally, an answer!"

    def generator(self):
        """a generator function that returns some elements on demand"""
        yield "one"
        yield "two"
        yield "three"

    def nan(self):
        return float("nan")

    def inf(self):
        return float("inf")

    @server.oneway
    def oneway_slow(self):
        """prints a message after a certain delay, and returns; but the client won't wait for it"""
        if self._verbose:
            print("%s - oneway_slow: waiting a bit..." % time.asctime())
        time.sleep(5)
        if self._verbose:
            print("%s - oneway_slow: returning result" % time.asctime())
        return "bogus return value"

    def _private(self):
        """a 'private' method that should not be accessible"""
        return "should not be allowed"

    def __private(self):
        """another 'private' method that should not be accessible"""
        return "should not be allowed"

    def __dunder__(self):
        """a double underscore method that should be accessible normally"""
        return "should be allowed (dunder)"

    def shutdown(self):
        """called to signal the echo server to shut down"""
        if self._verbose:
            print("%s - shutting down" % time.asctime())
        self._must_shutdown = True

    @property
    def verbose(self):
        return self._verbose

    @verbose.setter
    def verbose(self, onoff):
        self._verbose = bool(onoff)


class NameServer(threading.Thread):
    def __init__(self, hostname):
        super(NameServer, self).__init__()
        self.setDaemon(1)
        self.hostname = hostname
        self.started = threading.Event()

    def run(self):
        self.uri, self.ns_daemon, self.bc_server = nameserver.start_ns(self.hostname)
        self.started.set()
        if self.bc_server:
            self.bc_server.runInThread()
        self.ns_daemon.requestLoop()


def start_nameserver(host):
    ns = NameServer(host)
    ns.start()
    ns.started.wait()
    return ns


def main(args=None, returnWithoutLooping=False):
    parser = ArgumentParser(description="Pyro test echo/nameserver command line launcher.")
    parser.add_argument("-H", "--host", default="localhost", help="hostname to bind server on (default=%(default)s)")
    parser.add_argument("-p", "--port", type=int, default=0, help="port to bind server on")
    parser.add_argument("-u", "--unixsocket", help="Unix domain socket name to bind server on")
    parser.add_argument("-n", "--naming", action="store_true", default=False, help="register with nameserver")
    parser.add_argument("-N", "--nameserver", action="store_true", default=False, help="also start a nameserver")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="verbose output")
    parser.add_argument("-q", "--quiet", action="store_true", default=False, help="don't output anything")
    args = parser.parse_args(args)

    if args.verbose:
        args.quiet = False
    if not args.quiet:
        print("Starting Pyro's built-in test echo server.")
    config.SERVERTYPE = "multiplex"

    namesvr = None
    if args.nameserver:
        args.naming = True
        namesvr = start_nameserver(args.host)

    d = server.Daemon(host=args.host, port=args.port, unixsocket=args.unixsocket)
    echo = EchoServer()
    echo._verbose = args.verbose
    objectName = "test.echoserver"
    uri = d.register(echo, objectName)
    if args.naming:
        host, port = None, None
        if namesvr is not None:
            host, port = namesvr.uri.host, namesvr.uri.port
        ns = core.locate_ns(host, port)
        ns.register(objectName, uri)
        if args.verbose:
            print("using name server at %s" % ns._pyroUri)
            if namesvr is not None:
                if namesvr.bc_server:
                    print("broadcast server running at %s" % namesvr.bc_server.locationStr)
                else:
                    print("not using a broadcast server")
    else:
        if args.verbose:
            print("not using a name server.")
    if not args.quiet:
        print("object name: %s" % objectName)
        print("echo uri: %s" % uri)
        print("echoserver running.")

    if returnWithoutLooping:
        return d, echo, uri  # for unit testing
    else:
        d.requestLoop(loopCondition=lambda: not echo._must_shutdown)
    d.close()


if __name__ == "__main__":
    main()
