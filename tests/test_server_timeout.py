"""
Tests for a running Pyro server, with timeouts.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import test_server


class TestServerThreadTimeout(test_server.TestServerThreadNoTimeout):
    SERVERTYPE = "thread"
    COMMTIMEOUT = 2.0

    def testException(self):
        pass


class TestServerMultiplexTimeout(test_server.TestServerMultiplexNoTimeout):
    SERVERTYPE = "multiplex"
    COMMTIMEOUT = 2.0

    def testException(self):
        pass

