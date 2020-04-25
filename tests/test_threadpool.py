"""
Tests for the thread pool.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import time
import random
import pytest
from Pyro5 import socketutil, server
from Pyro5.svr_threads import Pool, PoolError, NoFreeWorkersError, SocketServer_Threadpool
from Pyro5 import config


JOB_TIME = 0.2


class Job(object):
    def __init__(self, name="unnamed"):
        self.name = name

    def __call__(self):
        time.sleep(JOB_TIME - random.random() / 10.0)


class SlowJob(object):
    def __init__(self, name="unnamed"):
        self.name = name

    def __call__(self):
        time.sleep(5*JOB_TIME - random.random() / 10.0)


class TestThreadPool:
    def setup_method(self):
        config.THREADPOOL_SIZE_MIN = 2
        config.THREADPOOL_SIZE = 4

    def teardown_method(self):
        config.reset()

    def testCreate(self):
        with Pool() as jq:
            _ = repr(jq)
        assert jq.closed

    def testSingle(self):
        with Pool() as p:
            job = Job()
            p.process(job)
            time.sleep(0.02)  # let it pick up the job
            assert len(p.busy) == 1

    def testAllBusy(self):
        try:
            config.COMMTIMEOUT = 0.2
            with Pool() as p:
                for i in range(config.THREADPOOL_SIZE):
                    p.process(SlowJob(str(i+1)))
                # putting one more than the number of workers should raise an error:
                with pytest.raises(NoFreeWorkersError):
                    p.process(SlowJob("toomuch"))
        finally:
            config.COMMTIMEOUT = 0.0

    def testClose(self):
        with Pool() as p:
            for i in range(config.THREADPOOL_SIZE):
                p.process(Job(str(i + 1)))
        with pytest.raises(PoolError):
            p.process(Job("1"))  # must not allow new jobs after closing
        assert len(p.busy) == 0
        assert len(p.idle) == 0

    def testScaling(self):
        with Pool() as p:
            for i in range(config.THREADPOOL_SIZE_MIN-1):
                p.process(Job("x"))
            assert len(p.idle) == 1
            assert len(p.busy) == config.THREADPOOL_SIZE_MIN-1
            p.process(Job("x"))
            assert len(p.idle) == 0
            assert len(p.busy) == config.THREADPOOL_SIZE_MIN
            # grow until no more free workers
            while True:
                try:
                    p.process(Job("x"))
                except NoFreeWorkersError:
                    break
            assert len(p.idle) == 0
            assert len(p.busy) == config.THREADPOOL_SIZE
            # wait till jobs are done and check ending situation
            time.sleep(JOB_TIME*1.5)
            assert len(p.busy) == 0
            assert len(p.idle) == config.THREADPOOL_SIZE_MIN


class ServerCallback(server.Daemon):
    def __init__(self):
        super().__init__()
        self.received_denied_reasons = []

    def _handshake(self, connection, denied_reason=None):
        self.received_denied_reasons.append(denied_reason)  # store the denied reason
        return True

    def handleRequest(self, connection):
        time.sleep(0.05)

    def _housekeeping(self):
        pass


class TestThreadPoolServer:
    def setup_method(self):
        config.THREADPOOL_SIZE_MIN = 1
        config.THREADPOOL_SIZE = 1
        config.POLLTIMEOUT = 0.5
        config.COMMTIMEOUT = 0.5

    def teardown_method(self):
        config.reset()

    def testServerPoolFull(self):
        port = socketutil.find_probably_unused_port()
        serv = SocketServer_Threadpool()
        daemon = ServerCallback()
        serv.init(daemon, "localhost", port)
        serversock = serv.sock.getsockname()
        csock1 = socketutil.create_socket(connect=serversock)
        csock2 = socketutil.create_socket(connect=serversock)
        try:
            serv.events([serv.sock])
            time.sleep(0.2)
            assert daemon.received_denied_reasons == [None]
            serv.events([serv.sock])
            time.sleep(0.2)
            assert len(daemon.received_denied_reasons) == 2
            assert "no free workers, increase server threadpool size" in daemon.received_denied_reasons
        finally:
            csock1.close()
            csock2.close()
            serv.shutdown()

