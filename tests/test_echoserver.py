"""
Tests for the built-in test echo server.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import time
import pytest
from threading import Thread, Event
import Pyro5.client
import Pyro5.errors
import Pyro5.utils.echoserver as echoserver
from Pyro5 import config


class EchoServerThread(Thread):
    def __init__(self):
        """
        Initialize the event loop

        Args:
            self: (todo): write your description
        """
        super(EchoServerThread, self).__init__()
        self.setDaemon(True)
        self.started = Event()
        self.echodaemon = self.echoserver = self.uri = None

    def run(self):
        """
        Run the main thread.

        Args:
            self: (todo): write your description
        """
        self.echodaemon, self.echoserver, self.uri = echoserver.main(args=["-q"], returnWithoutLooping=True)
        self.started.set()
        self.echodaemon.requestLoop(loopCondition=lambda: not self.echoserver._must_shutdown)


class TestEchoserver:
    def setup_method(self):
        """
        Initialize the thread.

        Args:
            self: (todo): write your description
        """
        self.echoserverthread = EchoServerThread()
        self.echoserverthread.start()
        self.echoserverthread.started.wait()
        self.uri = self.echoserverthread.uri

    def teardown_method(self):
        """
        Teardown the method.

        Args:
            self: (todo): write your description
        """
        self.echoserverthread.echodaemon.shutdown()
        time.sleep(0.02)
        self.echoserverthread.join()
        config.SERVERTYPE = "thread"

    def testExposed(self):
        """
        Deter test test test is enabled

        Args:
            self: (todo): write your description
        """
        e = Pyro5.utils.echoserver.EchoServer()
        assert hasattr(e, "_pyroExposed")

    def testEcho(self):
        """
        Evaluate the server.

        Args:
            self: (todo): write your description
        """
        with Pyro5.client.Proxy(self.uri) as echo:
            try:
                assert echo.echo("hello") == "hello"
                assert echo.echo(None) is None
                assert echo.echo([1,2,3]) == [1,2,3]
            finally:
                echo.shutdown()

    def testError(self):
        """
        Gets the traceback of this client.

        Args:
            self: (todo): write your description
        """
        with Pyro5.client.Proxy(self.uri) as echo:
            with pytest.raises(Exception) as x:
                echo.error()
            tb = "".join(Pyro5.errors.get_pyro_traceback(x.type, x.value, x.tb))
            assert "Remote traceback" in tb
            assert "ValueError" in tb
            assert str(x.value) == "this is the generated error from echoserver echo() method"
            with pytest.raises(Exception) as x:
                echo.error_with_text()
            tb = "".join(Pyro5.errors.get_pyro_traceback(x.type, x.value, x.tb))
            assert "Remote traceback" in tb
            assert "ValueError" in tb
            assert str(x.value) == "the message of the error"

    def testGenerator(self):
        """
        Generator that yields a generator. pyro5 generator.

        Args:
            self: (todo): write your description
        """
        with Pyro5.client.Proxy(self.uri) as echo:
            remotegenerator = echo.generator()
            assert isinstance(remotegenerator, Pyro5.client._StreamResultIterator)
            next(remotegenerator)
            next(remotegenerator)
            next(remotegenerator)
            with pytest.raises(StopIteration):
                next(remotegenerator)

