"""
Configuration settings.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import os
import copy
from . import _pyro_logfile, _pyro_loglevel


# Declare available config items.
# DO NOT EDIT THESE HERE! They are the system defaults!
# Instead, override them later in your own code or via environment variables.

HOST = "localhost"  # don't expose Pyro servers to the outside world by default
NS_HOST = HOST
NS_PORT = 9090  # tcp
NS_BCPORT = 9091  # udp
NS_BCHOST = None
NS_AUTOCLEAN = 0.0
NATHOST = None
NATPORT = 0
COMPRESSION = False
SERVERTYPE = "thread"
COMMTIMEOUT = 0.0
POLLTIMEOUT = 2.0  # seconds
MAX_RETRIES = 0
SOCK_REUSE = True  # so_reuseaddr on server sockets?
SOCK_NODELAY = False  # tcp_nodelay on socket?
ONEWAY_THREADED = True  # oneway calls run in their own thread
DETAILED_TRACEBACK = False
THREADPOOL_SIZE = 40
THREADPOOL_SIZE_MIN = 4
MAX_MESSAGE_SIZE = 1024 * 1024 * 1024  # 1 gigabyte
BROADCAST_ADDRS = ["<broadcast>", "0.0.0.0"]  # list of broadcast addresses to try, in this order
PREFER_IP_VERSION = 0  # 4, 6 or 0 (let OS choose according to RFC 3484)
SERIALIZER = "serpent"
SERIALIZERS_ACCEPTED = {"serpent", "marshal", "msgpack", "json"}  # these are the 'safe' serializers
LOGWIRE = False  # log wire-level messages
ITER_STREAMING = True
ITER_STREAM_LIFETIME = 0.0
ITER_STREAM_LINGER = 30.0
LOGFILE = _pyro_logfile
LOGLEVEL = _pyro_loglevel

del _pyro_logfile
del _pyro_loglevel


# store a copy of the config values as defaults
def _save_defaults():
    defaults = {}
    for key, value in globals().items():
        if key.startswith("_") or key in {"os", "copy"}:
            continue
        defaults[key] = copy.copy(value)
    return defaults
__defaults = _save_defaults()
assert len(__defaults) == 30
del _save_defaults


def reset(useenvironment=True):
    """
    Reset to default config items.
    If useenvironment is False, won't read environment variables settings (useful if you can't trust your env).
    """
    configitems = globals()
    for item, value in __defaults.items():
        configitems[item] = copy.copy(value)
    if useenvironment:
        PREFIX = "PYRO_"
        for item in __defaults:
            if PREFIX + item in os.environ:
                # environment variable overwrites config item
                value = __defaults[item]
                if value is not None:
                    envvalue = os.environ[PREFIX + item]
                    valuetype = type(value)
                    if valuetype is set:
                        envvalue = {v.strip() for v in envvalue.split(",")}
                    elif valuetype is list:
                        envvalue = [v.strip() for v in envvalue.split(",")]
                    elif valuetype is bool:
                        envvalue = envvalue.lower()
                        if envvalue in ("0", "off", "no", "false"):
                            envvalue = False
                        elif envvalue in ("1", "yes", "on", "true"):
                            envvalue = True
                        else:
                            raise ValueError("invalid boolean value: %s%s=%s" % (PREFIX, item, envvalue))
                    else:
                        envvalue = valuetype(envvalue)
                    configitems[item] = envvalue

reset()


def dump():
    """Easy config diagnostics"""
    import platform
    from .protocol import PROTOCOL_VERSION
    from . import __version__
    result = ["Pyro version: %s" % __version__,
              "Loaded from: %s" % os.path.dirname(__file__),
              "Python version: %s %s (%s, %s)" % (platform.python_implementation(), platform.python_version(), platform.system(), os.name),
              "Protocol version: %d" % PROTOCOL_VERSION,
              "Currently active configuration settings:"]
    for item in sorted(__defaults):
        value = globals()[item]
        result.append("{:s} = {:s}".format(item, str(value)))
    return "\n".join(result)


if __name__ == "__main__":
    print(dump())
