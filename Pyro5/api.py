"""
Single module that centralizes the main symbols from the Pyro5 API.
It imports most of the other packages that it needs
and provides shortcuts to the most frequently used objects and functions from those packages.
This means you can mostly just ``import Pyro5.api`` in your code to have access to most of
the Pyro5 objects and functions.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from . import __version__
from .configure import global_config as config
from .core import URI, locate_ns, resolve, type_meta
from .client import Proxy, BatchProxy, ConcurrentProxy, SerializedBlob
from .server import Daemon, DaemonObject, callback, expose, behavior, oneway, serve, Functor
from .nameserver import start_ns, start_ns_loop
from .serializers import SerializerBase
from .callcontext import current_context

register_dict_to_class = SerializerBase.register_dict_to_class
register_class_to_dict = SerializerBase.register_class_to_dict
unregister_dict_to_class = SerializerBase.unregister_dict_to_class
unregister_class_to_dict = SerializerBase.unregister_class_to_dict


__all__ = ["config", "URI", "locate_ns", "resolve", "type_meta", "current_context",
           "Proxy", "BatchProxy", "ConcurrentProxy", "SerializedBlob", "SerializerBase",
           "Daemon", "DaemonObject", "callback", "expose", "behavior", "oneway", "Functor",
           "start_ns", "start_ns_loop", "serve", "register_dict_to_class",
           "register_class_to_dict", "unregister_dict_to_class", "unregister_class_to_dict"]
