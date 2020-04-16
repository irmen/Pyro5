"""
Single module that centralizes the main symbols from the Pyro5 API

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from . import __version__
from .configure import global_config as config
from .core import URI, locate_ns, resolve, type_meta
from .client import Proxy, BatchProxy, SerializedBlob
from .server import Daemon, DaemonObject, callback, expose, behavior, oneway, serve
from .nameserver import start_ns, start_ns_loop
from .serializers import SerializerBase
from .callcontext import current_context


__all__ = ["config", "URI", "locate_ns", "resolve", "type_meta", "current_context",
           "Proxy", "BatchProxy", "SerializedBlob", "SerializerBase",
           "Daemon", "DaemonObject", "callback", "expose", "behavior", "oneway",
           "start_ns", "start_ns_loop", "serve"]
