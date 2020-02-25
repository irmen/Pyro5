"""
Single module that centralizes the main symbols from the Pyro5 API

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from . import __version__
from .configure import global_config as config
from .core import URI, locate_ns, resolve, type_meta, current_context
from .client import Proxy, BatchProxy, SerializedBlob
from .server import Daemon, DaemonObject, callback, expose, behavior, oneway
from .nameserver import start_ns, start_ns_loop
from .serializers import SerializerBase


# TODO move serveSimple to here instead of as a static function in the daemon? + adapt Pyro4 compat layer


__all__ = ["config", "URI", "locate_ns", "resolve", "type_meta", "current_context",
           "Proxy", "BatchProxy", "SerializedBlob", "SerializerBase",
           "Daemon", "DaemonObject", "callback", "expose", "behavior", "oneway",
           "start_ns", "start_ns_loop"]
