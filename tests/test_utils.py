import sys
import os
import io
import pytest
from Pyro5 import config, server, errors
from support import *


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


class TestUtils:
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

    def testResolveAttr(self):
        @server.expose
        class Exposed(object):
            def __init__(self, value):
                self.propvalue = value
                self.__value__ = value   # is not affected by the @expose

            def __str__(self):
                return "<%s>" % self.value

            def _p(self):
                return "should not be allowed"

            def __p(self):
                return "should not be allowed"

            def __p__(self):
                return "should be allowed (dunder)"

            @property
            def value(self):
                return self.propvalue

        class Unexposed(object):
            def __init__(self):
                self.value = 42

            def __value__(self):
                return self.value

        obj = Exposed("hello")
        obj.a = Exposed("a")
        obj.a.b = Exposed("b")
        obj.a.b.c = Exposed("c")
        obj.a._p = Exposed("p1")
        obj.a._p.q = Exposed("q1")
        obj.a.__p = Exposed("p2")
        obj.a.__p.q = Exposed("q2")
        obj.u = Unexposed()
        obj.u.v = Unexposed()
        # check the accessible attributes
        assert str(server._get_attribute(obj, "a")) == "<a>"
        dunder = str(server._get_attribute(obj, "__p__"))
        assert dunder.startswith("<bound method ")  # dunder is not private, part 1 of the check
        assert "Exposed.__p__ of" in dunder  # dunder is not private, part 2 of the check
        # check what should not be accessible
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "value")
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "propvalue")
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "__value__")  # is not affected by the @expose
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "_p")  # private
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "__p")  # private
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "a.b")
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "a.b.c")
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "a.b.c.d")
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "a._p")
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "a._p.q")
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "a.__p.q")
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "u")
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "u.v")
        with pytest.raises(AttributeError):
            server._get_attribute(obj, "u.v.value")


# TODO move this to server tests, remove doubles
class TestMetaAndExpose:
    def testBasic(self):
        o = MyThingFullExposed("irmen")
        m1 = server._get_exposed_members(o)
        m2 = server._get_exposed_members(MyThingFullExposed)
        assert m1 == m2
        keys = m1.keys()
        assert len(keys) == 3
        assert "methods" in keys
        assert "attrs" in keys
        assert "oneway" in keys

    def testGetExposedCacheWorks(self):
        class Thingy(object):
            def method1(self):
                pass
            @property
            def prop(self):
                return 1
            def notexposed(self):
                pass
        m1 = server._get_exposed_members(Thingy, only_exposed=False)
        def new_method(self, arg):
            return arg
        Thingy.new_method = new_method
        m2 = server._get_exposed_members(Thingy, only_exposed=False)
        assert m2, "should still be equal because result from cache" == m1

    def testPrivateNotExposed(self):
        o = MyThingFullExposed("irmen")
        m = server._get_exposed_members(o)
        assert m["methods"] == {"classmethod", "staticmethod", "method", "__dunder__", "oneway", "exposed"}
        assert m["attrs"] == {"prop1", "readonly_prop1", "prop2"}
        assert m["oneway"] == {"oneway"}
        o = MyThingPartlyExposed("irmen")
        m = server._get_exposed_members(o)
        assert m["methods"] == {"oneway", "exposed"}
        assert m["attrs"] == {"prop1", "readonly_prop1"}
        assert m["oneway"] == {"oneway"}

    def testNotOnlyExposed(self):
        o = MyThingPartlyExposed("irmen")
        m = server._get_exposed_members(o, only_exposed=False)
        assert m["methods"] == {"classmethod", "staticmethod", "method", "__dunder__", "oneway", "exposed"}
        assert m["attrs"] == {"prop1", "readonly_prop1", "prop2"}
        assert m["oneway"] == {"oneway"}

    def testPartlyExposedSubclass(self):
        o = MyThingPartlyExposedSub("irmen")
        m = server._get_exposed_members(o)
        assert m["attrs"] == {"prop1", "readonly_prop1"}
        assert m["oneway"] == {"oneway"}
        assert m["methods"] == {"sub_exposed", "exposed", "oneway"}

    def testExposedSubclass(self):
        o = MyThingExposedSub("irmen")
        m = server._get_exposed_members(o)
        assert m["attrs"] == {"readonly_prop1", "prop1", "prop2"}
        assert m["oneway"] == {"oneway", "oneway2"}
        assert m["methods"] == {"classmethod", "staticmethod", "oneway", "__dunder__", "method", "exposed",
                          "oneway2", "sub_exposed", "sub_unexposed"}

    def testExposePrivateFails(self):
        with pytest.raises(AttributeError):
            class Test1(object):
                @server.expose
                def _private(self):
                    pass
        with pytest.raises(AttributeError):
            class Test3(object):
                @server.expose
                def __private(self):
                    pass
        with pytest.raises(AttributeError):
            @server.expose
            class _Test4(object):
                pass
        with pytest.raises(AttributeError):
            @server.expose
            class __Test5(object):
                pass

    def testExposeDunderOk(self):
        class Test1(object):
            @server.expose
            def __dunder__(self):
                pass
        assert Test1.__dunder__._pyroExposed
        @server.expose
        class Test2(object):
            def __dunder__(self):
                pass
        assert Test2._pyroExposed
        assert Test2.__dunder__._pyroExposed

    def testClassmethodExposeWrongOrderFail(self):
        with pytest.raises(AttributeError) as ax:
            class TestClass:
                @server.expose
                @classmethod
                def cmethod(cls):
                    pass
        assert "must be done after" in str(ax.value)
        with pytest.raises(AttributeError) as ax:
            class TestClass:
                @server.expose
                @staticmethod
                def smethod(cls):
                    pass
        assert "must be done after" in str(ax.value)

    def testClassmethodExposeCorrectOrderOkay(self):
        class TestClass:
            @classmethod
            @server.expose
            def cmethod(cls):
                pass
            @staticmethod
            @server.expose
            def smethod(cls):
                pass
        assert TestClass.cmethod._pyroExposed
        assert TestClass.smethod._pyroExposed

    def testGetExposedProperty(self):
        o = MyThingFullExposed("irmen")
        with pytest.raises(AttributeError):
            server._get_exposed_property_value(o, "name")
        with pytest.raises(AttributeError):
            server._get_exposed_property_value(o, "c_attr")
        with pytest.raises(AttributeError):
            server._get_exposed_property_value(o, "propvalue")
        with pytest.raises(AttributeError):
            server._get_exposed_property_value(o, "unexisting_attribute")
        assert server._get_exposed_property_value(o, "prop1") == 42
        assert server._get_exposed_property_value(o, "prop2") == 42

    def testGetExposedPropertyFromPartiallyExposed(self):
        o = MyThingPartlyExposed("irmen")
        with pytest.raises(AttributeError):
            server._get_exposed_property_value(o, "name")
        with pytest.raises(AttributeError):
            server._get_exposed_property_value(o, "c_attr")
        with pytest.raises(AttributeError):
            server._get_exposed_property_value(o, "propvalue")
        with pytest.raises(AttributeError):
            server._get_exposed_property_value(o, "unexisting_attribute")
        assert server._get_exposed_property_value(o, "prop1") == 42
        with pytest.raises(AttributeError):
            server._get_exposed_property_value(o, "prop2")

    def testSetExposedProperty(self):
        o = MyThingFullExposed("irmen")
        with pytest.raises(AttributeError):
            server._set_exposed_property_value(o, "name", "erorr")
        with pytest.raises(AttributeError):
            server._set_exposed_property_value(o, "unexisting_attribute", 42)
        with pytest.raises(AttributeError):
            server._set_exposed_property_value(o, "readonly_prop1", 42)
        with pytest.raises(AttributeError):
            server._set_exposed_property_value(o, "propvalue", 999)
        assert o.prop1 == 42
        assert o.prop2 == 42
        server._set_exposed_property_value(o, "prop1", 999)
        assert o.propvalue == 999
        server._set_exposed_property_value(o, "prop2", 8888)
        assert o.propvalue == 8888

    def testSetExposedPropertyFromPartiallyExposed(self):
        o = MyThingPartlyExposed("irmen")
        with pytest.raises(AttributeError):
            server._set_exposed_property_value(o, "name", "erorr")
        with pytest.raises(AttributeError):
            server._set_exposed_property_value(o, "unexisting_attribute", 42)
        with pytest.raises(AttributeError):
            server._set_exposed_property_value(o, "readonly_prop1", 42)
        with pytest.raises(AttributeError):
            server._set_exposed_property_value(o, "propvalue", 999)
        assert o.prop1 == 42
        assert o.prop2 == 42
        server._set_exposed_property_value(o, "prop1", 999)
        assert o.propvalue == 999
        with pytest.raises(AttributeError):
            server._set_exposed_property_value(o, "prop2", 8888)

    def testIsPrivateName(self):
        assert server.is_private_attribute("_")
        assert server.is_private_attribute("__")
        assert server.is_private_attribute("___")
        assert server.is_private_attribute("_p")
        assert server.is_private_attribute("_pp")
        assert server.is_private_attribute("_p_")
        assert server.is_private_attribute("_p__")
        assert server.is_private_attribute("__p")
        assert server.is_private_attribute("___p")
        assert not server.is_private_attribute("__dunder__")  # dunder methods should not be private except a list of exceptions as tested below
        assert server.is_private_attribute("__init__")
        assert server.is_private_attribute("__call__")
        assert server.is_private_attribute("__new__")
        assert server.is_private_attribute("__del__")
        assert server.is_private_attribute("__repr__")
        assert server.is_private_attribute("__str__")
        assert server.is_private_attribute("__format__")
        assert server.is_private_attribute("__nonzero__")
        assert server.is_private_attribute("__bool__")
        assert server.is_private_attribute("__coerce__")
        assert server.is_private_attribute("__cmp__")
        assert server.is_private_attribute("__eq__")
        assert server.is_private_attribute("__ne__")
        assert server.is_private_attribute("__lt__")
        assert server.is_private_attribute("__gt__")
        assert server.is_private_attribute("__le__")
        assert server.is_private_attribute("__ge__")
        assert server.is_private_attribute("__hash__")
        assert server.is_private_attribute("__dir__")
        assert server.is_private_attribute("__enter__")
        assert server.is_private_attribute("__exit__")
        assert server.is_private_attribute("__copy__")
        assert server.is_private_attribute("__deepcopy__")
        assert server.is_private_attribute("__sizeof__")
        assert server.is_private_attribute("__getattr__")
        assert server.is_private_attribute("__setattr__")
        assert server.is_private_attribute("__hasattr__")
        assert server.is_private_attribute("__delattr__")
        assert server.is_private_attribute("__getattribute__")
        assert server.is_private_attribute("__instancecheck__")
        assert server.is_private_attribute("__subclasscheck__")
        assert server.is_private_attribute("__subclasshook__")
        assert server.is_private_attribute("__getinitargs__")
        assert server.is_private_attribute("__getnewargs__")
        assert server.is_private_attribute("__getstate__")
        assert server.is_private_attribute("__setstate__")
        assert server.is_private_attribute("__reduce__")
        assert server.is_private_attribute("__reduce_ex__")
