import sys
import os
import io
import pytest
from Pyro5 import config, errors


def crash(arg=100):
    pre1 = "black"
    pre2 = 999

    def nest(p1, p2):
        q = "white" + pre1
        x = pre2
        y = arg // 2
        p3 = p1 // p2
        return p3

    a = 10
    b = 0
    s = "hello"
    c = nest(a, b)
    return c


class TestErrors:
    def testFormatTracebackNormal(self):
        with pytest.raises(ZeroDivisionError) as x:
            crash()
        tb = "".join(errors.format_traceback(x.type, x.value, x.tb, detailed=False))
        assert "p3 = p1 // p2" in tb
        assert "ZeroDivisionError" in tb
        assert " a = 10" not in tb
        assert " s = 'whiteblack'" not in tb
        assert " pre2 = 999" not in tb
        assert " x = 999" not in  tb

    def testFormatTracebackDetail(self):
        with pytest.raises(ZeroDivisionError) as x:
            crash()
        tb = "".join(errors.format_traceback(x.type, x.value, x.tb, detailed=True))
        assert "p3 = p1 // p2" in tb
        assert "ZeroDivisionError" in tb
        assert " a = 10" in tb
        assert " q = 'whiteblack'" in tb
        assert " pre2 = 999" in tb
        assert " x = 999" in  tb

    def testPyroTraceback(self):
        try:
            crash()
        except ZeroDivisionError:
            pyro_tb = errors.format_traceback(detailed=True)
            assert " Extended stacktrace follows (most recent call last)\n" in pyro_tb
        try:
            crash("stringvalue")
        except TypeError as x:
            x._pyroTraceback = pyro_tb  # set the remote traceback info
            pyrotb = "".join(errors.get_pyro_traceback())
            assert "Remote traceback" in pyrotb
            assert "crash(\"stringvalue\")" in pyrotb
            assert "TypeError:" in pyrotb
            assert "ZeroDivisionError" in pyrotb
            del x._pyroTraceback
            pyrotb = "".join(errors.get_pyro_traceback())
            assert "Remote traceback" not in pyrotb
            assert "ZeroDivisionError" not in pyrotb
            assert "crash(\"stringvalue\")" in pyrotb
            assert "TypeError:" in pyrotb

    def testPyroTracebackArgs(self):
        try:
            crash()
        except ZeroDivisionError:
            ex_type, ex_value, ex_tb = sys.exc_info()
            tb1 = errors.get_pyro_traceback()
            tb2 = errors.get_pyro_traceback(ex_type, ex_value, ex_tb)
            assert tb2 == tb1
            tb1 = errors.format_traceback()
            tb2 = errors.format_traceback(ex_type, ex_value, ex_tb)
            assert tb2 == tb1
            tb2 = errors.format_traceback(detailed=True)
            assert tb1 != tb2

    def testExcepthook(self):
        # simply test the excepthook by calling it the way Python would
        try:
            crash()
        except ZeroDivisionError:
            pyro_tb = errors.format_traceback()
        with pytest.raises(TypeError) as x:
            crash("stringvalue")
        ex_type, ex_value, ex_tb = x.type, x.value, x.tb
        ex_value._pyroTraceback = pyro_tb  # set the remote traceback info
        oldstderr = sys.stderr
        try:
            sys.stderr = io.StringIO()
            errors.excepthook(ex_type, ex_value, ex_tb)
            output = sys.stderr.getvalue()
            assert "Remote traceback" in output
            assert "crash(\"stringvalue\")" in output
            assert "TypeError:" in output
            assert "ZeroDivisionError" in output
        finally:
            sys.stderr = oldstderr

    def clearEnv(self):
        if "PYRO_HOST" in os.environ:
            del os.environ["PYRO_HOST"]
        if "PYRO_NS_PORT" in os.environ:
            del os.environ["PYRO_NS_PORT"]
        if "PYRO_COMPRESSION" in os.environ:
            del os.environ["PYRO_COMPRESSION"]
        config.reset()

    def testConfig(self):
        self.clearEnv()
        try:
            assert config.NS_PORT == 9090
            assert config.HOST == "localhost"
            assert config.COMPRESSION == False
            os.environ["NS_PORT"] = "4444"
            config.reset()
            assert config.NS_PORT == 9090
            os.environ["PYRO_NS_PORT"] = "4444"
            os.environ["PYRO_HOST"] = "something.com"
            os.environ["PYRO_COMPRESSION"] = "OFF"
            config.reset()
            assert config.NS_PORT == 4444
            assert config.HOST == "something.com"
            assert config.COMPRESSION == False
        finally:
            self.clearEnv()
            assert config.NS_PORT == 9090
            assert config.HOST == "localhost"
            assert config.COMPRESSION == False

    def testConfigReset(self):
        try:
            config.reset()
            assert config.HOST == "localhost"
            config.HOST = "foobar"
            assert config.HOST == "foobar"
            config.reset()
            assert config.HOST == "localhost"
            os.environ["PYRO_HOST"] = "foobar"
            config.reset()
            assert config.HOST == "foobar"
            del os.environ["PYRO_HOST"]
            config.reset()
            assert config.HOST == "localhost"
        finally:
            self.clearEnv()
