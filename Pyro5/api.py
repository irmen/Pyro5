"""
One stop API module.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from . import __version__, config
from .core import URI, locate_ns, resolve, type_meta, current_context
from .client import Proxy, BatchProxy, SerializedBlob
from .server import Daemon, DaemonObject, callback, expose, behavior, oneway
from .nameserver import start_ns, start_ns_loop

__all__ = ["config", "URI", "locate_ns", "resolve", "type_meta", "current_context",
           "Proxy", "BatchProxy", "SerializedBlob",
           "Daemon", "DaemonObject", "callback", "expose", "behavior", "oneway",
           "start_ns", "start_ns_loop"]
