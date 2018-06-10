"""
An effort to provide a backward-compatible Pyro4 API layer,
to make porting existing code from Pyro4 to Pyro5 easier.

This only works for code that imported Pyro4 symbols from the Pyro4 module
directly, instead of from one of Pyro4's sub modules. So, for instance:
    from Pyro4 import Proxy
instead of
    from Pyro4.core import Proxy

*some* submodules are more or less emulated such as Pyro4.errors, Pyro4.socketutil.

So, you may first have to convert your old code to use the importing scheme to
only import the Pyro4 module and not from its submodules, and then you should
insert this at the top to enable the compatibility layer:
    from Pyro5.compatibility import Pyro4


Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

# the symbols that were available in Pyro4 as Pyro4.* :
# from Pyro4.core import URI, Proxy, Daemon, callback, batch, asyncproxy, oneway, expose, behavior, current_context
# from Pyro4.core import _locateNS as locateNS, _resolve as resolve
# from Pyro4.futures import Future

import sys
from .. import api
from .. import errors
from .. import serializers
from .. import socketutil as socketutil_pyro5


__all__ = ["config", "URI", "Proxy", "Daemon", "callback", "batch",
           "asyncproxy", "oneway", "expose", "behavior", "current_context",
           "locateNS", "resolve", "Future", "errors"]


# symbols that are no longer available in Pyro5 and that we don't emulate:

def asyncproxy(*args, **kwargs):
    raise NotImplementedError("async proxy is no longer available in Pyro5")


class Future(object):
    def __init__(self, *args):
        raise NotImplementedError("Pyro5 no longer provides its own Future class, "
                                  "you should use Python's concurrent.futures module instead for that")


class NamespaceInterceptor:
    def __init__(self, namespace):
        self.namespace = namespace

    def __getattr__(self, item):
        raise NotImplementedError("The Pyro4 compatibility layer doesn't provide the Pyro4.{0} namespace, "
                                  "first make sure the code only uses symbols from the Pyro4 package directly"
                                  .format(self.namespace))


naming = NamespaceInterceptor("naming")
core = NamespaceInterceptor("core")


# compatibility wrappers for the other symbols:

__version__ = api.__version__
config = api.config
callback = api.callback
oneway = api.oneway
expose = api.expose
behavior = api.behavior
current_context = api.current_context


def config_asDict():
    raise NotImplementedError()  # @todo


config.asDict = config_asDict
del config_asDict


class URI(api.URI):
    # @todo check class methods
    pass


class Proxy(api.Proxy):
    # @todo check class methods
    def _pyroAsync(self, asynchronous=True):
        raise NotImplementedError("async proxy is no longer available in Pyro5")


class Daemon(api.Daemon):
    # @todo check class methods
    pass


def locateNS(host=None, port=None, broadcast=True, hmac_key=None):
    if hmac_key:
        raise NotImplementedError("hmac_key is no longer available in Pyro5, consider using 2-way SSL instead")
    return api.locate_ns(host, port, broadcast)


def resolve(uri, hmac_key=None):
    if hmac_key:
        raise NotImplementedError("hmac_key is no longer available in Pyro5, consider using 2-way SSL instead")
    return api.resolve(uri)


class BatchProxy(api.BatchProxy):
    def __call__(self, oneway=False, asynchronous=False):
        if asynchronous:
            raise NotImplementedError("async proxy is no longer available in Pyro5")
        return super().__call__(oneway)


def batch(proxy):
    return BatchProxy(proxy)


class UtilModule:
    @staticmethod
    def getPyroTraceback(ex_type=None, ex_value=None, ex_tb=None):
        return errors.get_pyro_traceback(ex_type, ex_value, ex_tb)

    @staticmethod
    def formatTraceback(ex_type=None, ex_value=None, ex_tb=None, detailed=False):
        return errors.format_traceback(ex_type, ex_value, ex_tb, detailed)

    SerializerBase = serializers.SerializerBase

    def excepthook(self, *args, **kwargs):
        return errors.excepthook(*args, **kwargs)


util = UtilModule()


class SocketUtilModule:
    @staticmethod
    def getIpVersion(hostnameOrAddress):
        return socketutil_pyro5.get_ip_version(hostnameOrAddress)

    @staticmethod
    def getIpAddress(hostname, workaround127=False, ipVersion=None):
        return socketutil_pyro5.get_ip_address(hostname, workaround127, ipVersion)

    @staticmethod
    def getInterfaceAddress(ip_address):
        return socketutil_pyro5.get_interface_address(ip_address)


socketutil = SocketUtilModule()


# make sure that subsequent  from Pyro4 import ...  will work:
sys.modules["Pyro4"] = sys.modules[__name__]
sys.modules["Pyro4.errors"] = errors
sys.modules["Pyro4.core"] = core
sys.modules["Pyro4.naming"] = naming
sys.modules["Pyro4.util"] = util
sys.modules["Pyro4.socketutil"] = socketutil
