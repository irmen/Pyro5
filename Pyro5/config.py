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

HOST = "localhost"
NS_HOST = "localhost"
NS_PORT = 9090
NS_BCPORT = 9091
NS_BCHOST = None
NS_AUTOCLEAN = 0.0
NATHOST = None
NATPORT = 0
COMPRESSION = False
SERVERTYPE = "thread"
COMMTIMEOUT = 0.0  # seconds
POLLTIMEOUT = 2.0  # seconds
MAX_RETRIES = 0
SOCK_REUSE = True  # so_reuseaddr on server sockets?
SOCK_NODELAY = False  # tcp_nodelay on socket?
DETAILED_TRACEBACK = False
THREADPOOL_SIZE = 40        # @todo still use this?
THREADPOOL_SIZE_MIN = 4     # @todo still use this?
MAX_MESSAGE_SIZE = 1024 * 1024 * 1024  # 1 gigabyte
BROADCAST_ADDRS = ["<broadcast>", "0.0.0.0"]
PREFER_IP_VERSION = 0  # 4, 6 or 0 (let OS choose according to RFC 3484)
SERIALIZER = "serpent"
LOGWIRE = False
ITER_STREAMING = True
ITER_STREAM_LIFETIME = 0.0
ITER_STREAM_LINGER = 30.0
LOGFILE = _pyro_logfile
LOGLEVEL = _pyro_loglevel
SSL = False
SSL_SERVERCERT = ""
SSL_SERVERKEY = ""
SSL_SERVERKEYPASSWD = ""
SSL_REQUIRECLIENTCERT = False
SSL_CLIENTCERT = ""
SSL_CLIENTKEY = ""
SSL_CLIENTKEYPASSWD = ""
SSL_CACERTS = ""


del _pyro_logfile
del _pyro_loglevel


__correct_configitems = {item for item in globals()
                         if not item.startswith("_") and item not in {"os", "copy", "dump", "reset", "as_dict"}}


def _config_items():
    return __correct_configitems


def _check_configitems():
    wrong = _config_items() - __correct_configitems
    if wrong:
        raise RuntimeError("invalid Pyro config item(s) set: "+", ".join(wrong))


# store a copy of the config values as defaults
def _save_defaults():
    defaults = {}
    g = globals()
    for key in _config_items():
        defaults[key] = copy.copy(g[key])
    return defaults


__defaults = _save_defaults()
assert len(__defaults) == 37
del _save_defaults


def _read_env():
    PREFIX = "PYRO_"
    configitems = globals()
    for item, envvalue in (e for e in os.environ.items() if e[0].startswith(PREFIX)):
        item = item[len(PREFIX):]
        value = __defaults.get(item)
        if value is None:
            raise ValueError("invalid Pyro environment config variable: %s%s" % (PREFIX, item))
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


_read_env()


def reset(useenvironment=True):
    """
    Reset to default config items.
    If useenvironment is False, won't read environment variables settings (useful if you can't trust your env).
    """
    configitems = globals()
    for item, value in __defaults.items():
        configitems[item] = copy.copy(value)
    if useenvironment:
        _read_env()  # environment variables overwrite config items


def as_dict():
    return {item: value for item, value in globals().items() if item in __correct_configitems}


def dump():
    """Easy config diagnostics"""
    import platform
    from .protocol import PROTOCOL_VERSION
    from . import __version__
    _check_configitems()
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
