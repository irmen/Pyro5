"""
Tests for the core logic.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import os
import copy
import uuid
import pytest
import importlib
import logging
import Pyro5.core
import Pyro5.callcontext
import Pyro5.client
import Pyro5.errors
import Pyro5.configure
import Pyro5.server
from Pyro5 import config


class TestCore:
    def test_uri(self):
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("burp")
        u1 = Pyro5.core.URI("PYRO:obj@host:5555")
        u2 = copy.copy(u1)
        assert str(u1) == str(u2)
        assert u1 == u2
        assert u1 is not u2

    def test_unix_uri(self):
        p = Pyro5.core.URI("PYRO:12345@./u:/tmp/sockname")
        assert p.object == "12345"
        assert p.sockname == "/tmp/sockname"
        p = Pyro5.core.URI("PYRO:12345@./u:../sockname")
        assert p.object == "12345"
        assert p.sockname == "../sockname"
        p = Pyro5.core.URI("PYRO:12345@./u:/path with spaces/sockname  ")
        assert p.object == "12345"
        assert p.sockname == "/path with spaces/sockname  "

    def testConfig(self):
        assert type(config.COMPRESSION) is bool
        assert type(config.NS_PORT) is int
        cfgdict = config.as_dict()
        assert type(cfgdict) is dict
        assert "COMPRESSION" in cfgdict
        assert config.COMPRESSION == cfgdict["COMPRESSION"]

    def testConfigDefaults(self):
        # some security sensitive settings:
        config.reset(False)   # reset the config to default
        assert config.HOST == "localhost"
        assert config.NS_HOST == "localhost"
        assert config.SERIALIZER == "serpent"

    def testConfigValid(self):
        with pytest.raises(AttributeError):
            config.XYZ_FOOBAR = True  # don't want to allow weird config names

    def testConfigParseBool(self):
        config = Pyro5.configure.Configuration()
        assert type(config.COMPRESSION) is bool
        os.environ["PYRO_COMPRESSION"] = "yes"
        config.reset()
        assert config.COMPRESSION
        os.environ["PYRO_COMPRESSION"] = "off"
        config.reset()
        assert not config.COMPRESSION
        os.environ["PYRO_COMPRESSION"] = "foobar"
        with pytest.raises(ValueError):
            config.reset()
        del os.environ["PYRO_COMPRESSION"]
        config.reset()

    def testConfigDump(self):
        config = Pyro5.configure.Configuration()
        dump = config.dump()
        assert "version:" in dump
        assert "LOGLEVEL" in dump

    def testLogInit(self):
        _ = logging.getLogger("Pyro5")
        os.environ["PYRO_LOGLEVEL"] = "DEBUG"
        os.environ["PYRO_LOGFILE"] = "{stderr}"
        importlib.reload(Pyro5)
        _ = logging.getLogger("Pyro5")
        os.environ["PYRO_LOGFILE"] = "Pyro.log"
        importlib.reload(Pyro5)
        _ = logging.getLogger("Pyro5")
        del os.environ["PYRO_LOGLEVEL"]
        del os.environ["PYRO_LOGFILE"]
        importlib.reload(Pyro5)
        _ = logging.getLogger("Pyro5")

    def testUriStrAndRepr(self):
        uri = "PYRONAME:some_obj_name"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri
        uri = "PYRONAME:some_obj_name@host.com"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri + ":" + str(config.NS_PORT)  # a PYRONAME uri with a hostname gets a port too if omitted
        uri = "PYRONAME:some_obj_name@host.com:8888"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri
        expected = "<Pyro5.core.URI at 0x%x; PYRONAME:some_obj_name@host.com:8888>" % id(p)
        assert repr(p) == expected
        uri = "PYRO:12345@host.com:9999"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri
        uri = "PYRO:12345@./u:sockname"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri
        uri = "PYRO:12345@./u:sockname"
        assert str(p) == uri
        assert type(p.sockname) is str
        uri = "PYRO:12345@./u:sock name with strings"
        p = Pyro5.core.URI(uri)
        assert str(p) == uri

    def testUriParsingPyro(self):
        p = Pyro5.core.URI("PYRONAME:some_obj_name")
        assert p.protocol == "PYRONAME"
        assert p.object == "some_obj_name"
        assert p.host is None
        assert p.sockname is None
        assert p.port is None
        p = Pyro5.core.URI("PYRONAME:some_obj_name@host.com:9999")
        assert p.protocol == "PYRONAME"
        assert p.object == "some_obj_name"
        assert p.host == "host.com"
        assert p.port == 9999

        p = Pyro5.core.URI("PYRO:12345@host.com:4444")
        assert p.protocol == "PYRO"
        assert p.object == "12345"
        assert p.host == "host.com"
        assert p.sockname is None
        assert p.port == 4444
        assert p.location == "host.com:4444"
        p = Pyro5.core.URI("PYRO:12345@./u:sockname")
        assert p.object == "12345"
        assert p.sockname == "sockname"
        p = Pyro5.core.URI("PYRO:12345@./u:/tmp/sockname")
        assert p.object == "12345"
        assert p.sockname == "/tmp/sockname"
        p = Pyro5.core.URI("PYRO:12345@./u:/path with spaces/sockname  ")
        assert p.object == "12345"
        assert p.sockname == "/path with spaces/sockname  "
        p = Pyro5.core.URI("PYRO:12345@./u:../sockname")
        assert p.object == "12345"
        assert p.sockname == "../sockname"
        p = Pyro5.core.URI("pyro:12345@host.com:4444")
        assert p.protocol == "PYRO"
        assert p.object == "12345"
        assert p.host == "host.com"
        assert p.sockname is None
        assert p.port == 4444

    def testUriParsingIpv6(self):
        p = Pyro5.core.URI("pyro:12345@[::1]:4444")
        assert p.host == "::1"
        assert p.location == "[::1]:4444"
        with pytest.raises(Pyro5.errors.PyroError) as e:
            Pyro5.core.URI("pyro:12345@[[::1]]:4444")
        assert str(e.value) == "invalid ipv6 address: enclosed in too many brackets"
        with pytest.raises(Pyro5.errors.PyroError) as e:
            Pyro5.core.URI("pyro:12345@[must_be_numeric_here]:4444")
        assert str(e.value) == "invalid ipv6 address: the part between brackets must be a numeric ipv6 address"

    def testUriParsingPyroname(self):
        p = Pyro5.core.URI("PYRONAME:objectname")
        assert p.protocol == "PYRONAME"
        assert p.object == "objectname"
        assert p.host is None
        assert p.port is None
        p = Pyro5.core.URI("PYRONAME:objectname@nameserverhost")
        assert p.protocol == "PYRONAME"
        assert p.object == "objectname"
        assert p.host == "nameserverhost"
        assert p.port == config.NS_PORT  # Pyroname uri with host gets a port too if not specified
        p = Pyro5.core.URI("PYRONAME:objectname@nameserverhost:4444")
        assert p.protocol == "PYRONAME"
        assert p.object == "objectname"
        assert p.host == "nameserverhost"
        assert p.port == 4444
        p = Pyro5.core.URI("PyroName:some_obj_name@host.com:9999")
        assert p.protocol == "PYRONAME"
        p = Pyro5.core.URI("pyroname:some_obj_name@host.com:9999")
        assert p.protocol == "PYRONAME"

    def testUriParsingPyrometa(self):
        p = Pyro5.core.URI("PYROMETA:meta")
        assert p.protocol == "PYROMETA"
        assert p.object == {"meta"}
        assert p.host is None
        assert p.port is None
        p = Pyro5.core.URI("PYROMETA:meta1,meta2,meta2@nameserverhost")
        assert p.protocol == "PYROMETA"
        assert p.object == {"meta1", "meta2"}
        assert p.host == "nameserverhost"
        assert p.port == config.NS_PORT  # PyroMeta uri with host gets a port too if not specified
        p = Pyro5.core.URI("PYROMETA:meta@nameserverhost:4444")
        assert p.protocol == "PYROMETA"
        assert p.object == {"meta"}
        assert p.host == "nameserverhost"
        assert p.port == 4444
        p = Pyro5.core.URI("PyroMeta:meta1,meta2@host.com:9999")
        assert p.protocol == "PYROMETA"
        p = Pyro5.core.URI("PyroMeta:meta1,meta2@host.com:9999")
        assert p.protocol == "PYROMETA"

    def testInvalidUris(self):
        with pytest.raises(TypeError):
            Pyro5.core.URI(None)
        with pytest.raises(TypeError):
            Pyro5.core.URI(99999)
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI(" ")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("a")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYR")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO::")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:a")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:x@")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:x@hostname")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:@hostname:portstr")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:@hostname:7766")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:objid@hostname:7766:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:obj id@hostname:7766")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROLOC:objname")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROLOC:objname@host")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROLOC:objectname@hostname:4444")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRONAME:")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRONAME:obj name@nameserver:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRONAME:objname@nameserver:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRONAME:objname@nameserver:7766:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROMETA:")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROMETA:meta@nameserver:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROMETA:meta@nameserver:7766:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYROMETA:meta1, m2 ,m3@nameserver:7766:bogus")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("FOOBAR:")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("FOOBAR:objid@hostname:7766")
        with pytest.raises(Pyro5.errors.PyroError):
            Pyro5.core.URI("PYRO:12345@./u:sockname:9999")

    def testUriUnicode(self):
        p = Pyro5.core.URI("PYRO:12345@host.com:4444")
        assert p.protocol == "PYRO"
        assert p.object == "12345"
        assert p.host == "host.com"
        assert type(p.protocol) is str
        assert type(p.object) is str
        assert type(p.host) is str
        assert p.sockname is None
        assert p.port == 4444

        uri = "PYRO:12345@hostname:9999"
        p = Pyro5.core.URI(uri)
        unicodeuri = "PYRO:weirdchars" + chr(0x20ac) + "@host" + chr(0x20AC) + ".com:4444"
        pu = Pyro5.core.URI(unicodeuri)
        assert pu.protocol == "PYRO"
        assert pu.host == "host" + chr(0x20AC) + ".com"
        assert pu.object == "weirdchars" + chr(0x20AC)
        assert str(pu) == "PYRO:weirdchars" + chr(0x20ac) + "@host" + chr(0x20ac) + ".com:4444"
        expected = ("<Pyro5.core.URI at 0x%x; PYRO:weirdchars" + chr(0x20ac) + "@host" + chr(0x20ac) + ".com:4444>") % id(pu)
        assert repr(pu) == expected
        assert str(pu) == "PYRO:weirdchars" + chr(0x20ac) + "@host" + chr(0x20ac) + ".com:4444"

    def testUriCopy(self):
        p1 = Pyro5.core.URI("PYRO:12345@hostname:9999")
        p2 = Pyro5.core.URI(p1)
        p3 = copy.copy(p1)
        assert p2.protocol == p1.protocol
        assert p2.host == p1.host
        assert p2.port == p1.port
        assert p2.object == p1.object
        assert p2 == p1
        assert p3.protocol == p1.protocol
        assert p3.host == p1.host
        assert p3.port == p1.port
        assert p3.object == p1.object
        assert p3 == p1

    def testUriSubclassCopy(self):
        class SubURI(Pyro5.core.URI):
            pass
        u = SubURI("PYRO:12345@hostname:9999")
        u2 = copy.copy(u)
        assert isinstance(u2, SubURI)

    def testUriEqual(self):
        p1 = Pyro5.core.URI("PYRO:12345@host.com:9999")
        p2 = Pyro5.core.URI("PYRO:12345@host.com:9999")
        p3 = Pyro5.core.URI("PYRO:99999@host.com:4444")
        assert p2 == p1
        assert p1 != p3
        assert p2 != p3
        assert p1 == p2
        assert p1 != p3
        assert p2 != p3
        assert p1 == p2
        assert p1 != p3
        assert p2 != p3
        assert hash(p1) == hash(p2)
        assert hash(p1) != hash(p3)
        p2.port = 4444
        p2.object = "99999"
        assert p1 != p2
        assert p3 == p2
        assert p1 != p2
        assert p2 == p3
        assert p1 != p2
        assert p2 == p3
        assert hash(p1) != hash(p2)
        assert hash(p2) == hash(p3)
        assert p1 != 42

    def testLocation(self):
        assert Pyro5.core.URI.isUnixsockLocation("./u:name")
        assert not(Pyro5.core.URI.isUnixsockLocation("./p:name"))
        assert not(Pyro5.core.URI.isUnixsockLocation("./x:name"))
        assert not(Pyro5.core.URI.isUnixsockLocation("foobar"))

    def testCallContext(self):
        ctx = Pyro5.callcontext.current_context
        corr_id = uuid.UUID('1897022f-c481-4117-a4cc-cbd1ca100582')
        ctx.correlation_id = corr_id
        d = ctx.to_global()
        assert isinstance(d, dict)
        assert d["correlation_id"] == corr_id
        corr_id2 = uuid.UUID('67b05ad9-2d6a-4ed8-8ed5-95cba68b4cf9')
        d["correlation_id"] = corr_id2
        ctx.from_global(d)
        assert Pyro5.callcontext.current_context.correlation_id == corr_id2
        Pyro5.callcontext.current_context.correlation_id = None

