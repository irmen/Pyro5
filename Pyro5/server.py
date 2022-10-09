"""
Server related classes (Daemon etc)

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import os
import sys
import uuid
import time
import socket
import collections
import threading
import logging
import inspect
import warnings
import weakref
import serpent
import ipaddress
from typing import TypeVar, Tuple, Union, Optional, Dict, Any, Sequence, Set
from . import config, core, errors, serializers, socketutil, protocol, client
from .callcontext import current_context
from collections.abc import Callable

__all__ = ["Daemon", "DaemonObject", "callback", "expose", "behavior", "oneway", "serve"]

log = logging.getLogger("Pyro5.server")


_private_dunder_methods = frozenset([
    "__init__", "__init_subclass__", "__class__", "__module__", "__weakref__",
    "__call__", "__new__", "__del__", "__repr__",
    "__str__", "__format__", "__nonzero__", "__bool__", "__coerce__",
    "__cmp__", "__eq__", "__ne__", "__hash__", "__ge__", "__gt__", "__le__", "__lt__",
    "__dir__", "__enter__", "__exit__", "__copy__", "__deepcopy__", "__sizeof__",
    "__getattr__", "__setattr__", "__hasattr__", "__getattribute__", "__delattr__",
    "__instancecheck__", "__subclasscheck__", "__getinitargs__", "__getnewargs__",
    "__getstate__", "__setstate__", "__reduce__", "__reduce_ex__", "__subclasshook__"
])


def is_private_attribute(attr_name: str) -> bool:
    """returns if the attribute name is to be considered private or not."""
    if attr_name in _private_dunder_methods:
        return True
    if not attr_name.startswith('_'):
        return False
    if len(attr_name) > 4 and attr_name.startswith("__") and attr_name.endswith("__"):
        return False
    return True


# decorators

def callback(method: Callable) -> Callable:
    """
    decorator to mark a method to be a 'callback'. This will make Pyro
    raise any errors also on the callback side, and not only on the side
    that does the callback call.
    """
    method._pyroCallback = True     # type: ignore
    return method


def oneway(method: Callable) -> Callable:
    """
    decorator to mark a method to be oneway (client won't wait for a response)
    """
    method._pyroOneway = True       # type: ignore
    return method


_T = TypeVar("_T", bound=Union[Callable, type])


def expose(method_or_class: _T) -> _T:
    """
    Decorator to mark a method or class to be exposed for remote calls.
    You can apply it to a method or a class as a whole.
    If you need to change the default instance mode or instance creator, also use a @behavior decorator.
    """
    if inspect.isdatadescriptor(method_or_class):
        func = method_or_class.fget or method_or_class.fset or method_or_class.fdel     # type: ignore
        if is_private_attribute(func.__name__):
            raise AttributeError("exposing private names (starting with _) is not allowed")
        func._pyroExposed = True
        return method_or_class
    attrname = getattr(method_or_class, "__name__", None)
    if not attrname or isinstance(method_or_class, (classmethod, staticmethod)):
        # we could be dealing with a descriptor (classmethod/staticmethod), this means the order of the decorators is wrong
        if inspect.ismethoddescriptor(method_or_class):
            attrname = method_or_class.__get__(None, dict).__name__     # type: ignore
            raise AttributeError("using @expose on a classmethod/staticmethod must be done "
                                 "after @classmethod/@staticmethod. Method: " + attrname)
        else:
            raise AttributeError("@expose cannot determine what this is: "+repr(method_or_class))
    if is_private_attribute(attrname):
        raise AttributeError("exposing private names (starting with _) is not allowed")
    if inspect.isclass(method_or_class):
        clazz = method_or_class
        log.debug("exposing all members of %r", clazz)
        for name in clazz.__dict__:
            if is_private_attribute(name):
                continue
            thing = getattr(clazz, name)
            if inspect.isfunction(thing) or inspect.ismethoddescriptor(thing):
                thing._pyroExposed = True
            elif inspect.ismethod(thing):
                thing.__func__._pyroExposed = True
            elif inspect.isdatadescriptor(thing):
                if getattr(thing, "fset", None):
                    thing.fset._pyroExposed = True
                if getattr(thing, "fget", None):
                    thing.fget._pyroExposed = True
                if getattr(thing, "fdel", None):
                    thing.fdel._pyroExposed = True
        clazz._pyroExposed = True       # type: ignore
        return clazz
    method_or_class._pyroExposed = True     # type: ignore
    return method_or_class


def behavior(instance_mode: str = "session", instance_creator: Optional[Callable] = None) -> Callable:
    """
    Decorator to specify the server behavior of your Pyro class.
    """
    def _behavior(clazz):
        if not inspect.isclass(clazz):
            raise TypeError("behavior decorator can only be used on a class")
        if instance_mode not in ("single", "session", "percall"):
            raise ValueError("invalid instance mode: " + instance_mode)
        if instance_creator and not callable(instance_creator):
            raise TypeError("instance_creator must be a callable")
        clazz._pyroInstancing = (instance_mode, instance_creator)
        return clazz
    if not isinstance(instance_mode, str):
        raise SyntaxError("behavior decorator is missing argument(s)")
    return _behavior


@expose
class DaemonObject(object):
    """The part of the daemon that is exposed as a Pyro object."""

    def __init__(self, daemon):
        self.daemon = daemon

    def registered(self):
        """returns a list of all object names registered in this daemon"""
        return list(self.daemon.objectsById.keys())

    def ping(self):
        """a simple do-nothing method for testing purposes"""
        pass

    def info(self):
        """return some descriptive information about the daemon"""
        return "%s bound on %s, NAT %s, %d objects registered. Servertype: %s" % (
            core.DAEMON_NAME, self.daemon.locationStr, self.daemon.natLocationStr,
            len(self.daemon.objectsById), self.daemon.transportServer)

    def get_metadata(self, objectId):
        """
        Get metadata for the given object (exposed methods, oneways, attributes).
        """
        obj = _unpack_weakref(self.daemon.objectsById.get(objectId))
        if obj is not None:
            metadata = _get_exposed_members(obj)
            if not metadata["methods"] and not metadata["attrs"]:
                # Something seems wrong: nothing is remotely exposed.
                warnings.warn("Class %r doesn't expose any methods or attributes. Did you forget setting @expose on them?" % type(obj))
            return metadata
        else:
            log.debug("unknown object requested: %s", objectId)
            raise errors.DaemonError("unknown object")

    def get_next_stream_item(self, streamId):
        if streamId not in self.daemon.streaming_responses:
            raise errors.PyroError("item stream terminated")
        client, timestamp, linger_timestamp, stream = self.daemon.streaming_responses[streamId]
        if client is None:
            # reset client connection association (can be None if proxy disconnected)
            self.daemon.streaming_responses[streamId] = (current_context.client, timestamp, 0, stream)
        try:
            return next(stream)
        except Exception:
            # in case of error (or StopIteration!) the stream is removed
            del self.daemon.streaming_responses[streamId]
            raise

    def close_stream(self, streamId):
        if streamId in self.daemon.streaming_responses:
            del self.daemon.streaming_responses[streamId]


class Daemon(object):
    """
    Pyro daemon. Contains server side logic and dispatches incoming remote method calls
    to the appropriate objects.
    """

    def __init__(self, host=None, port=0, unixsocket=None, nathost=None, natport=None, interface=DaemonObject, connected_socket=None):
        if connected_socket:
            nathost = natport = None
        else:
            if host is None:
                host = config.HOST
            elif not isinstance(host, str):
                host = str(host)  # take care of the occasion where host is an ipaddress.IpAddress
            if nathost is None:
                nathost = config.NATHOST
            elif not isinstance(nathost, str):
                nathost = str(nathost)  # take care of the occasion where host is an ipaddress.IpAddress
            if natport is None and nathost is not None:
                natport = config.NATPORT
            if nathost and unixsocket:
                raise ValueError("cannot use nathost together with unixsocket")
            if (nathost is None) ^ (natport is None):
                raise ValueError("must provide natport with nathost")
        self.__mustshutdown = threading.Event()
        self.__mustshutdown.set()
        self.__loopstopped = threading.Event()
        self.__loopstopped.set()
        if connected_socket:
            from .svr_existingconn import SocketServer_ExistingConnection
            self.transportServer = SocketServer_ExistingConnection()
            self.transportServer.init(self, connected_socket)
        else:
            if config.SERVERTYPE == "thread":
                from .svr_threads import SocketServer_Threadpool
                self.transportServer = SocketServer_Threadpool()
            elif config.SERVERTYPE == "multiplex":
                from .svr_multiplex import SocketServer_Multiplex
                self.transportServer = SocketServer_Multiplex()
            else:
                raise errors.PyroError("invalid server type '%s'" % config.SERVERTYPE)
            self.transportServer.init(self, host, port, unixsocket)
        #: The location (str of the form ``host:portnumber``) on which the Daemon is listening
        self.locationStr = self.transportServer.locationStr
        log.debug("daemon created on %s - %s (pid %d)", self.locationStr, socketutil.family_str(self.transportServer.sock), os.getpid())
        natport_for_loc = natport
        if natport == 0:
            # expose internal port number as NAT port as well. (don't use port because it could be 0 and will be chosen by the OS)
            natport_for_loc = int(self.locationStr.split(":")[1])
        # The NAT-location (str of the form ``nathost:natportnumber``) on which the Daemon is exposed for use with NAT-routing
        self.natLocationStr = "%s:%d" % (nathost, natport_for_loc) if nathost else None
        if self.natLocationStr:
            log.debug("NAT address is %s", self.natLocationStr)
        pyroObject = interface(self)
        pyroObject._pyroId = core.DAEMON_NAME
        # Dictionary from Pyro object id to the actual Pyro object registered by this id
        self.objectsById = {pyroObject._pyroId: pyroObject}
        log.debug("pyro protocol version: %d" % protocol.PROTOCOL_VERSION)
        self._pyroInstances = {}   # pyro objects for instance_mode=single (singletons, just one per daemon)
        self.streaming_responses = {}   # stream_id -> (client, creation_timestamp, linger_timestamp, stream)
        self.housekeeper_lock = threading.Lock()
        self.create_single_instance_lock = threading.Lock()
        self.__mustshutdown.clear()
        self.methodcall_error_handler = _default_methodcall_error_handler

    @property
    def sock(self):
        """the server socket used by the daemon"""
        return self.transportServer.sock

    @property
    def sockets(self):
        """list of all sockets used by the daemon (server socket and all active client sockets)"""
        return self.transportServer.sockets

    @property
    def selector(self):
        """the multiplexing selector used, if using the multiplex server type"""
        return self.transportServer.selector

    @staticmethod
    def serveSimple(objects, host=None, port=0, daemon=None, ns=True, verbose=True) -> None:
        """
        Backwards compatibility method to fire up a daemon and start serving requests.
        New code should just use the global ``serve`` function instead.
        """
        serve(objects, host, port, daemon, ns, verbose)

    def requestLoop(self, loopCondition=lambda: True) -> None:
        """
        Goes in a loop to service incoming requests, until someone breaks this
        or calls shutdown from another thread.
        """
        self.__mustshutdown.clear()
        log.info("daemon %s entering requestloop", self.locationStr)
        try:
            self.__loopstopped.clear()
            self.transportServer.loop(loopCondition=lambda: not self.__mustshutdown.is_set() and loopCondition())
        finally:
            self.__loopstopped.set()
        log.debug("daemon exits requestloop")

    def events(self, eventsockets):
        """for use in an external event loop: handle any requests that are pending for this daemon"""
        return self.transportServer.events(eventsockets)

    def shutdown(self):
        """Cleanly terminate a daemon that is running in the requestloop."""
        log.debug("daemon shutting down")
        self.streaming_responses = {}
        time.sleep(0.02)
        self.__mustshutdown.set()
        if self.transportServer:
            self.transportServer.shutdown()
            time.sleep(0.02)
        self.close()
        self.__loopstopped.wait(timeout=5)  # use timeout to avoid deadlock situations

    @property
    def _shutting_down(self):
        return self.__mustshutdown.is_set()

    def _handshake(self, conn, denied_reason=None):
        """
        Perform connection handshake with new clients.
        Client sends a MSG_CONNECT message with a serialized data payload.
        If all is well, return with a CONNECT_OK message.
        The reason we're not doing this with a MSG_INVOKE method call on the daemon
        (like when retrieving the metadata) is because we need to force the clients
        to get past an initial connect handshake before letting them invoke any method.
        Return True for successful handshake, False if something was wrong.
        If a denied_reason is given, the handshake will fail with the given reason.
        """
        serializer_id = serializers.MarshalSerializer.serializer_id
        msg_seq = 0
        try:
            msg = protocol.recv_stub(conn, [protocol.MSG_CONNECT])
            msg_seq = msg.seq
            if denied_reason:
                raise Exception(denied_reason)
            if config.LOGWIRE:
                protocol.log_wiredata(log, "daemon handshake received", msg)
            if msg.flags & protocol.FLAGS_CORR_ID:
                current_context.correlation_id = uuid.UUID(bytes=msg.corr_id)
            else:
                current_context.correlation_id = uuid.uuid4()
            serializer_id = msg.serializer_id
            serializer = serializers.serializers_by_id[serializer_id]
            data = serializer.loads(msg.data)
            handshake_response = self.validateHandshake(conn, data["handshake"])
            handshake_response = {
                "handshake": handshake_response,
                "meta": self.objectsById[core.DAEMON_NAME].get_metadata(data["object"])
            }
            data = serializer.dumps(handshake_response)
            msgtype = protocol.MSG_CONNECTOK
        except errors.ConnectionClosedError:
            log.debug("handshake failed, connection closed early")
            return False
        except Exception as x:
            log.debug("handshake failed, reason:", exc_info=True)
            serializer = serializers.serializers_by_id[serializer_id]
            data = serializer.dumps(str(x))
            msgtype = protocol.MSG_CONNECTFAIL
        # We need a minimal amount of response data or the socket will remain blocked
        # on some systems... (messages smaller than 40 bytes)
        msg = protocol.SendingMessage(msgtype, 0, msg_seq, serializer_id, data, annotations=self.__annotations())
        if config.LOGWIRE:
            protocol.log_wiredata(log, "daemon handshake response", msg)
        conn.send(msg.data)
        return msg.type == protocol.MSG_CONNECTOK

    def validateHandshake(self, conn, data):
        """
        Override this to create a connection validator for new client connections.
        It should return a response data object normally if the connection is okay,
        or should raise an exception if the connection should be denied.
        """
        return "hello"

    def clientDisconnect(self, conn):
        """
        Override this to handle a client disconnect.
        Conn is the SocketConnection object that was disconnected.
        """
        pass

    def handleRequest(self, conn):
        """
        Handle incoming Pyro request. Catches any exception that may occur and
        wraps it in a reply to the calling side, as to not make this server side loop
        terminate due to exceptions caused by remote invocations.
        """
        request_flags = 0
        request_seq = 0
        request_serializer_id = serializers.MarshalSerializer.serializer_id
        wasBatched = False
        isCallback = False
        try:
            msg = protocol.recv_stub(conn, [protocol.MSG_INVOKE, protocol.MSG_PING])
        except errors.CommunicationError as x:
            # we couldn't even get data from the client, this is an immediate error
            # log.info("error receiving data from client %s: %s", conn.sock.getpeername(), x)
            raise x
        try:
            request_flags = msg.flags
            request_seq = msg.seq
            request_serializer_id = msg.serializer_id
            if msg.flags & protocol.FLAGS_CORR_ID:
                current_context.correlation_id = uuid.UUID(bytes=msg.corr_id)
            else:
                current_context.correlation_id = uuid.uuid4()
            if config.LOGWIRE:
                protocol.log_wiredata(log, "daemon wiredata received", msg)
            if msg.type == protocol.MSG_PING:
                # return same seq, but ignore any data (it's a ping, not an echo). Nothing is deserialized.
                msg = protocol.SendingMessage(protocol.MSG_PING, 0, msg.seq, msg.serializer_id, b"pong", annotations=self.__annotations())
                if config.LOGWIRE:
                    protocol.log_wiredata(log, "daemon wiredata sending", msg)
                conn.send(msg.data)
                return
            serializer = serializers.serializers_by_id[msg.serializer_id]
            if request_flags & protocol.FLAGS_KEEPSERIALIZED:
                # pass on the wire protocol message blob unchanged
                objId, method, vargs, kwargs = self.__deserializeBlobArgs(msg)
            else:
                # normal deserialization of remote call arguments
                objId, method, vargs, kwargs = serializer.loadsCall(msg.data)
            current_context.client = conn
            try:
                # store, because on oneway calls, socket will be disconnected:
                current_context.client_sock_addr = conn.sock.getpeername()
            except socket.error:
                current_context.client_sock_addr = None  # sometimes getpeername() doesn't work...
            current_context.seq = msg.seq
            current_context.annotations = msg.annotations
            current_context.msg_flags = msg.flags
            current_context.serializer_id = msg.serializer_id
            del msg  # invite GC to collect the object, don't wait for out-of-scope
            obj = _unpack_weakref(self.objectsById.get(objId))
            if obj is not None:
                if inspect.isclass(obj):
                    obj = self._getInstance(obj, conn)
                if request_flags & protocol.FLAGS_BATCH:
                    # batched method calls, loop over them all and collect all results
                    data = []
                    for method, vargs, kwargs in vargs:
                        method = _get_attribute(obj, method)
                        try:
                            result = method(*vargs, **kwargs)  # this is the actual method call to the Pyro object
                        except Exception as xv:
                            self.methodcall_error_handler(self, current_context.client_sock_addr, method, vargs, kwargs, xv)
                            xv._pyroTraceback = errors.format_traceback(detailed=config.DETAILED_TRACEBACK)
                            data.append(core._ExceptionWrapper(xv))
                            break  # stop processing the rest of the batch
                        else:
                            data.append(result)    # note that we don't support streaming results in batch mode
                    wasBatched = True
                else:
                    # normal single method call
                    if method == "__getattr__":
                        # special case for direct attribute access (only exposed @properties are accessible)
                        data = _get_exposed_property_value(obj, vargs[0])
                    elif method == "__setattr__":
                        # special case for direct attribute access (only exposed @properties are accessible)
                        data = _set_exposed_property_value(obj, vargs[0], vargs[1])
                    else:
                        method = _get_attribute(obj, method)
                        if request_flags & protocol.FLAGS_ONEWAY:
                            # oneway call to be run inside its own thread, otherwise client blocking can still occur
                            #    on the next call on the same proxy
                            _OnewayCallThread(method, vargs, kwargs, self, current_context.client_sock_addr).start()
                        else:
                            isCallback = getattr(method, "_pyroCallback", False)
                            try:
                                data = method(*vargs, **kwargs)  # this is the actual method call to the Pyro object
                            except Exception as xv:
                                self.methodcall_error_handler(self, current_context.client_sock_addr, method, vargs, kwargs, xv)
                                raise
                            if not request_flags & protocol.FLAGS_ONEWAY:
                                isStream, data = self._streamResponse(data, conn)
                                if isStream:
                                    # throw an exception as well as setting message flags
                                    # this way, it is backwards compatible with older pyro versions.
                                    exc = errors.ProtocolError("result of call is an iterator")
                                    ann = {"STRM": data.encode()} if data else {}
                                    self._sendExceptionResponse(conn, request_seq, serializer.serializer_id, exc, None,
                                                                annotations=ann, flags=protocol.FLAGS_ITEMSTREAMRESULT)
                                    return
            else:
                log.debug("unknown object requested: %s", objId)
                raise errors.DaemonError("unknown object")
            if request_flags & protocol.FLAGS_ONEWAY:
                return  # oneway call, don't send a response
            else:
                data = serializer.dumps(data)
                response_flags = 0
                if wasBatched:
                    response_flags |= protocol.FLAGS_BATCH
                msg = protocol.SendingMessage(protocol.MSG_RESULT, response_flags, request_seq, serializer.serializer_id, data,
                                              annotations=self.__annotations())
                current_context.response_annotations = {}
                if config.LOGWIRE:
                    protocol.log_wiredata(log, "daemon wiredata sending", msg)
                conn.send(msg.data)
        except Exception as xv:
            msg = getattr(xv, "pyroMsg", None)
            if msg:
                request_seq = msg.seq
                request_serializer_id = msg.serializer_id
            if not isinstance(xv, errors.ConnectionClosedError):
                if not request_flags & protocol.FLAGS_ONEWAY:
                    if isinstance(xv, errors.SerializeError) or not isinstance(xv, errors.CommunicationError):
                        # only return the error to the client if it wasn't a oneway call, and not a communication error
                        # (in these cases, it makes no sense to try to report the error back to the client...)
                        tblines = errors.format_traceback(detailed=config.DETAILED_TRACEBACK)
                        self._sendExceptionResponse(conn, request_seq, request_serializer_id, xv, tblines)
            if isCallback or isinstance(xv, (errors.CommunicationError, errors.SecurityError)):
                raise  # re-raise if flagged as callback, communication or security error.

    def _clientDisconnect(self, conn):
        if config.ITER_STREAM_LINGER > 0:
            # client goes away, keep streams around for a bit longer (allow reconnect)
            for streamId in list(self.streaming_responses):
                info = self.streaming_responses.get(streamId, None)
                if info and info[0] is conn:
                    _, timestamp, _, stream = info
                    self.streaming_responses[streamId] = (None, timestamp, time.time(), stream)
        else:
            # client goes away, close any streams it had open as well
            for streamId in list(self.streaming_responses):
                info = self.streaming_responses.get(streamId, None)
                if info and info[0] is conn:
                    del self.streaming_responses[streamId]
        self.clientDisconnect(conn)  # user overridable hook

    def _housekeeping(self):
        """
        Perform periodical housekeeping actions (cleanups etc)
        """
        if self._shutting_down:
            return
        with self.housekeeper_lock:
            if self.streaming_responses:
                if config.ITER_STREAM_LIFETIME > 0:
                    # cleanup iter streams that are past their lifetime
                    for streamId in list(self.streaming_responses.keys()):
                        info = self.streaming_responses.get(streamId, None)
                        if info:
                            last_use_period = time.time() - info[1]
                            if 0 < config.ITER_STREAM_LIFETIME < last_use_period:
                                del self.streaming_responses[streamId]
                if config.ITER_STREAM_LINGER > 0:
                    # cleanup iter streams that are past their linger time
                    for streamId in list(self.streaming_responses.keys()):
                        info = self.streaming_responses.get(streamId, None)
                        if info and info[2]:
                            linger_period = time.time() - info[2]
                            if linger_period > config.ITER_STREAM_LINGER:
                                del self.streaming_responses[streamId]
            self.housekeeping()

    def housekeeping(self):
        """
        Override this to add custom periodic housekeeping (cleanup) logic.
        This will be called every few seconds by the running daemon's request loop.
        """
        pass

    def _getInstance(self, clazz, conn):
        """
        Find or create a new instance of the class
        """
        def createInstance(clazz, creator):
            try:
                if creator:
                    obj = creator(clazz)
                    if isinstance(obj, clazz):
                        return obj
                    raise TypeError("instance creator returned object of different type")
                return clazz()
            except Exception:
                log.exception("could not create pyro object instance")
                raise
        instance_mode, instance_creator = clazz._pyroInstancing
        if instance_mode == "single":
            # create and use one singleton instance of this class (not a global singleton, just exactly one per daemon)
            with self.create_single_instance_lock:
                instance = self._pyroInstances.get(clazz)
                if not instance:
                    log.debug("instancemode %s: creating new pyro object for %s", instance_mode, clazz)
                    instance = createInstance(clazz, instance_creator)
                    self._pyroInstances[clazz] = instance
                return instance
        elif instance_mode == "session":
            # Create and use one instance for this proxy connection
            # the instances are kept on the connection object.
            # (this is the default instance mode when using new style @expose)
            instance = conn.pyroInstances.get(clazz)
            if not instance:
                log.debug("instancemode %s: creating new pyro object for %s", instance_mode, clazz)
                instance = createInstance(clazz, instance_creator)
                conn.pyroInstances[clazz] = instance
            return instance
        elif instance_mode == "percall":
            # create and use a new instance just for this call
            log.debug("instancemode %s: creating new pyro object for %s", instance_mode, clazz)
            return createInstance(clazz, instance_creator)
        else:
            raise errors.DaemonError("invalid instancemode in registered class")

    def _sendExceptionResponse(self, connection, seq, serializer_id, exc_value, tbinfo, flags=0, annotations=None):
        """send an exception back including the local traceback info"""
        exc_value._pyroTraceback = tbinfo
        serializer = serializers.serializers_by_id[serializer_id]
        try:
            data = serializer.dumps(exc_value)
        except Exception:
            # the exception object couldn't be serialized, use a generic PyroError instead
            xt, xv, tb = sys.exc_info()
            msg = "Error serializing exception: %s. Original exception: %s: %s" % (str(xv), type(exc_value), str(exc_value))
            exc_value = errors.PyroError(msg)
            exc_value._pyroTraceback = tbinfo
            data = serializer.dumps(exc_value)
        flags |= protocol.FLAGS_EXCEPTION
        annotations = dict(annotations or {})
        annotations.update(self.annotations())
        msg = protocol.SendingMessage(protocol.MSG_RESULT, flags, seq, serializer.serializer_id, data, annotations=annotations)
        if config.LOGWIRE:
            protocol.log_wiredata(log, "daemon wiredata sending (error response)", msg)
        connection.send(msg.data)

    def register(self, obj_or_class, objectId=None, force=False, weak=False):
        """
        Register a Pyro object under the given id. Note that this object is now only
        known inside this daemon, it is not automatically available in a name server.
        This method returns a URI for the registered object.
        Pyro checks if an object is already registered, unless you set force=True.
        You can register a class or an object (instance) directly.
        For a class, Pyro will create instances of it to handle the remote calls according
        to the instance_mode (set via @expose on the class). The default there is one object
        per session (=proxy connection). If you register an object directly, Pyro will use
        that single object for *all* remote calls.
        With *weak=True*, only weak reference to the object will be stored, and the object will
        get unregistered from the daemon automatically when garbage-collected.
        """
        if objectId:
            if not isinstance(objectId, str):
                raise TypeError("objectId must be a string or None")
        else:
            objectId = "obj_" + uuid.uuid4().hex  # generate a new objectId
        if inspect.isclass(obj_or_class):
            if weak: raise TypeError("Classes cannot be registered with weak=True.")
            if not hasattr(obj_or_class, "_pyroInstancing"):
                obj_or_class._pyroInstancing = ("session", None)
        if not force:
            if hasattr(obj_or_class, "_pyroId") and obj_or_class._pyroId != "":  # check for empty string is needed for Cython
                raise errors.DaemonError("object or class already has a Pyro id")
            if objectId in self.objectsById:
                raise errors.DaemonError("an object or class is already registered with that id")
        # set some pyro attributes
        obj_or_class._pyroId = objectId
        obj_or_class._pyroDaemon = self
        # register a custom serializer for the type to automatically return proxies
        # we need to do this for all known serializers
        for ser in serializers.serializers.values():
            if inspect.isclass(obj_or_class):
                ser.register_type_replacement(obj_or_class, _pyro_obj_to_auto_proxy)
            else:
                ser.register_type_replacement(type(obj_or_class), _pyro_obj_to_auto_proxy)
        # register the object/class in the mapping
        self.objectsById[obj_or_class._pyroId] = (obj_or_class if not weak else weakref.ref(obj_or_class))
        if weak: weakref.finalize(obj_or_class,self.unregister,objectId)
        return self.uriFor(objectId)

    def unregister(self, objectOrId):
        """
        Remove a class or object from the known objects inside this daemon.
        You can unregister the class/object directly, or with its id.
        """
        if objectOrId is None:
            raise ValueError("object or objectid argument expected")
        if not isinstance(objectOrId, str):
            objectId = getattr(objectOrId, "_pyroId", None)
            if objectId is None:
                raise errors.DaemonError("object isn't registered")
        else:
            objectId = objectOrId
            objectOrId = None
        if objectId == core.DAEMON_NAME:
            return
        if objectId in self.objectsById:
            del self.objectsById[objectId]
            if objectOrId is not None:
                del objectOrId._pyroId
                del objectOrId._pyroDaemon
                # Don't remove the custom type serializer because there may be
                # other registered objects of the same type still depending on it.

    def uriFor(self, objectOrId, nat=True):
        """
        Get a URI for the given object (or object id) from this daemon.
        Only a daemon can hand out proper uris because the access location is
        contained in them.
        Note that unregistered objects cannot be given an uri, but unregistered
        object names can (it's just a string we're creating in that case).
        If nat is set to False, the configured NAT address (if any) is ignored and it will
        return an URI for the internal address.
        """
        if not isinstance(objectOrId, str):
            objectOrId = getattr(objectOrId, "_pyroId", None)
            if objectOrId is None or objectOrId not in self.objectsById:
                raise errors.DaemonError("object isn't registered in this daemon")
        if nat:
            loc = self.natLocationStr or self.locationStr
        else:
            loc = self.locationStr
        return core.URI("PYRO:%s@%s" % (objectOrId, loc))

    def resetMetadataCache(self, objectOrId, nat=True):
        """Reset cache of metadata when a Daemon has available methods/attributes
        dynamically updated.  Clients will have to get a new proxy to see changes"""
        uri = self.uriFor(objectOrId, nat)
        # can only be cached if registered, else no-op
        if uri.object in self.objectsById:
            registered_object = _unpack_weakref(self.objectsById[uri.object])
            # Clear cache regardless of how it is accessed
            _reset_exposed_members(registered_object)

    def proxyFor(self, objectOrId, nat=True):
        """
        Get a fully initialized Pyro Proxy for the given object (or object id) for this daemon.
        If nat is False, the configured NAT address (if any) is ignored.
        The object or id must be registered in this daemon, or you'll get an exception.
        (you can't get a proxy for an unknown object)
        """
        uri = self.uriFor(objectOrId, nat)
        proxy = client.Proxy(uri)
        try:
            registered_object = _unpack_weakref(self.objectsById[uri.object])
        except KeyError:
            raise errors.DaemonError("object isn't registered in this daemon")
        meta = _get_exposed_members(registered_object)
        proxy._pyroGetMetadata(known_metadata=meta)
        return proxy

    def close(self):
        """Close down the server and release resources"""
        self.__mustshutdown.set()
        self.streaming_responses = {}
        if self.transportServer:
            log.debug("daemon closing")
            self.transportServer.close()
            self.transportServer = None

    def annotations(self):
        """Override to return a dict with custom user annotations to be sent with each response message."""
        return {}

    def combine(self, daemon):
        """
        Combines the event loop of the other daemon in the current daemon's loop.
        You can then simply run the current daemon's requestLoop to serve both daemons.
        This works fine on the multiplex server type, but doesn't work with the threaded server type.
        """
        log.debug("combining event loop with other daemon")
        self.transportServer.combine_loop(daemon.transportServer)

    def __annotations(self):
        annotations = current_context.response_annotations
        annotations.update(self.annotations())
        return annotations

    def __repr__(self):
        if hasattr(self, "locationStr"):
            family = socketutil.family_str(self.sock)
            return "<%s.%s at 0x%x; %s - %s; %d objects>" % (self.__class__.__module__, self.__class__.__name__,
                                                             id(self), self.locationStr, family, len(self.objectsById))
        else:
            # daemon objects may come back from serialized form without being properly initialized (by design)
            return "<%s.%s at 0x%x; unusable>" % (self.__class__.__module__, self.__class__.__name__, id(self))

    def __enter__(self):
        if not self.transportServer:
            raise errors.PyroError("cannot reuse this object")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __getstate__(self):
        # A little hack to make it possible to serialize Pyro objects, because they can reference a daemon,
        # but it is not meant to be able to properly serialize/deserialize Daemon objects.
        return tuple()

    def __setstate__(self, state):
        assert len(state) == 0

    def _streamResponse(self, data, client):
        if isinstance(data, collections.abc.Iterator) or inspect.isgenerator(data):
            if config.ITER_STREAMING:
                if type(data) in (type({}.keys()), type({}.values()), type({}.items())):
                    raise errors.PyroError("won't serialize or stream lazy dict iterators, convert to list yourself")
                stream_id = str(uuid.uuid4())
                self.streaming_responses[stream_id] = (client, time.time(), 0, data)
                return True, stream_id
            return True, None
        return False, data

    def __deserializeBlobArgs(self, protocolmsg):
        import marshal
        blobinfo = protocolmsg.annotations["BLBI"]
        blobinfo, objId, method = marshal.loads(blobinfo)
        blob = client.SerializedBlob(blobinfo, protocolmsg, is_blob=True)
        return objId, method, (blob,), {}  # object, method, vargs, kwargs


def serve(objects: Dict[Any, str], host: Optional[Union[str, ipaddress.IPv4Address, ipaddress.IPv6Address]] = None,
          port: int = 0, daemon: Optional[Daemon] = None, use_ns: bool = True, verbose: bool = True) -> None:
    """
    Basic method to fire up a daemon (or supply one yourself).
    objects is a dict containing objects to register as keys, and
    their names (or None) as values. If ns is true they will be registered
    in the naming server as well, otherwise they just stay local.
    If you need to publish on a unix domain socket, or require finer control of the daemon's
    behavior, you can't use this shortcut method. Create a Daemon yourself and use its
    appropriate methods.
    See the documentation on 'publishing objects' (in chapter: Servers) for more details.
    """
    if daemon is None:
        daemon = Daemon(host, port)
    with daemon:
        ns = core.locate_ns() if use_ns else None
        for obj, name in objects.items():
            if ns:
                localname = None  # name is used for the name server
            else:
                localname = name  # no name server, use name in daemon
            uri = daemon.register(obj, localname)
            if verbose:
                print("Object {0}:\n    uri = {1}".format(repr(obj), uri))
            if name and ns:
                ns.register(name, uri)
                if verbose:
                    print("    name = {0}".format(name))
        if verbose:
            print("Pyro daemon running.")
        daemon.requestLoop()


def _default_methodcall_error_handler(daemon: Daemon, client_sock: socketutil.SocketConnection,
                                      method: Callable, vargs: Sequence[Any], kwargs: Dict[str, Any],
                                      exception: Exception) -> None:
    """The default routine called to process a exception raised in the user code of a method call"""
    log.debug("exception occurred in method call user code: client={} method={} exception={}"
              .format(client_sock, method.__qualname__, repr(exception)))


# register the special serializers for the pyro objects
serpent.register_class(Daemon, serializers.pyro_class_serpent_serializer)
serializers.SerializerBase.register_class_to_dict(Daemon, serializers.serialize_pyro_object_to_dict, serpent_too=False)


def _pyro_obj_to_auto_proxy(obj: Any) -> Any:
    """reduce function that automatically replaces Pyro objects by a Proxy"""
    daemon = getattr(obj, "_pyroDaemon", None)
    if daemon:
        # only return a proxy if the object is a registered pyro object
        return daemon.proxyFor(obj)
    return obj


def _get_attribute(obj: Any, attr: str) -> Any:
    """
    Resolves an attribute name to an object.  Raises
    an AttributeError if any attribute in the chain starts with a '``_``'.
    Doesn't resolve a dotted name, because that is a security vulnerability.
    It treats it as a single attribute name (and the lookup will likely fail).
    """
    if is_private_attribute(attr):
        raise AttributeError("attempt to access private attribute '%s'" % attr)
    else:
        obj = getattr(obj, attr)
    if getattr(obj, "_pyroExposed", False):
        return obj
    raise AttributeError("attempt to access unexposed attribute '%s'" % attr)


__exposed_member_cache = {}     # type: Dict[Tuple[type, bool], Dict[str, Set[str]]]


def _reset_exposed_members(obj: Any, only_exposed: bool = True) -> None:
    """Delete any cached exposed members forcing recalculation on next request"""
    if not inspect.isclass(obj):
        obj = obj.__class__
    cache_key = (obj, only_exposed)
    __exposed_member_cache.pop(cache_key, None)


def _get_exposed_members(obj: Any, only_exposed: bool = True) -> Dict[str, Set[str]]:
    """
    Return public and exposed members of the given object's class.
    You can also provide a class directly.
    Private members are ignored no matter what (names starting with underscore).
    If only_exposed is True, only members tagged with the @expose decorator are
    returned. If it is False, all public members are returned.
    The return value consists of the exposed methods, exposed attributes, and methods
    tagged as @oneway.
    (All this is used as meta data that Pyro sends to the proxy if it asks for it)
    """
    if not inspect.isclass(obj):
        obj = obj.__class__

    cache_key = (obj, only_exposed)
    if cache_key in __exposed_member_cache:
        return __exposed_member_cache[cache_key]

    methods = set()  # all methods
    oneway = set()  # oneway methods
    attrs = set()  # attributes
    for m in dir(obj):      # also lists names inherited from super classes
        if is_private_attribute(m):
            continue
        v = getattr(obj, m)
        if inspect.ismethod(v) or inspect.isfunction(v) or inspect.ismethoddescriptor(v):
            if getattr(v, "_pyroExposed", not only_exposed):
                methods.add(m)
                # check if the method is marked with the 'oneway' decorator:
                if getattr(v, "_pyroOneway", False):
                    oneway.add(m)
        elif inspect.isdatadescriptor(v):
            func = getattr(v, "fget", None) or getattr(v, "fset", None) or getattr(v, "fdel", None)
            if func is not None and getattr(func, "_pyroExposed", not only_exposed):
                attrs.add(m)
        # Note that we don't expose plain class attributes no matter what.
        # it is a syntax error to add a decorator on them, and it is not possible
        # to give them a _pyroExposed tag either.
        # The way to expose attributes is by using properties for them.
        # This automatically solves the protection/security issue: you have to
        # explicitly decide to make an attribute into a @property (and to @expose it)
        # before it becomes remotely accessible.
    result = {
        "methods": methods,
        "oneway": oneway,
        "attrs": attrs
    }
    __exposed_member_cache[cache_key] = result
    return result


def _unpack_weakref(obj: Any):
    """
    Unpack weak reference, or return the object itself, if not a weak reference.
    If the weak reference is dead (calling it returns None), raises an
    exception. Even though register(...,weak=True) creates finalizer which
    will delete the weakref from the mapping, it is possible that the object
    is garbage-collected asynchronously between obtaining weakref from the
    mapping and reference unpacking, making the weakref invalid; this is handled
    by the exception here.
    """
    if not isinstance(obj,weakref.ref): return obj
    ret=obj() # ret will hold strong reference to obj, until it gets deleted itself
    if ret is None: raise errors.DaemonError("Weakly registered deleted meanwhile (or finalizer failed?).")
    return ret

def _get_exposed_property_value(obj: Any, propname: str, only_exposed: bool = True) -> Any:
    """
    Return the value of an @exposed @property.
    If the requested property is not a @property or not exposed,
    an AttributeError is raised instead.
    """
    v = getattr(obj.__class__, propname)
    if inspect.isdatadescriptor(v):
        if v.fget and getattr(v.fget, "_pyroExposed", not only_exposed):
            return v.fget(obj)
    raise AttributeError("attempt to access unexposed or unknown remote attribute '%s'" % propname)


def _set_exposed_property_value(obj: Any, propname: str, value: Any, only_exposed: bool = True) -> Any:
    """
    Sets the value of an @exposed @property.
    If the requested property is not a @property or not exposed,
    an AttributeError is raised instead.
    """
    v = getattr(obj.__class__, propname)
    if inspect.isdatadescriptor(v):
        pfunc = v.fget or v.fset or v.fdel
        if v.fset and getattr(pfunc, "_pyroExposed", not only_exposed):
            return v.fset(obj, value)
    raise AttributeError("attempt to access unexposed or unknown remote attribute '%s'" % propname)


class _OnewayCallThread(threading.Thread):
    def __init__(self, pyro_method, vargs, kwargs, pyro_daemon, pyro_client_sock):
        super(_OnewayCallThread, self).__init__(target=self._methodcall, name="oneway-call")
        self.daemon = True
        self.parent_context = current_context.to_global()
        self.pyro_daemon = pyro_daemon
        self.pyro_client_sock = pyro_client_sock
        self.pyro_method = pyro_method
        self.pyro_vargs = vargs
        self.pyro_kwars = kwargs

    def run(self):
        current_context.from_global(self.parent_context)
        super(_OnewayCallThread, self).run()

    def _methodcall(self):
        try:
            self.pyro_method(*self.pyro_vargs, **self.pyro_kwars)
        except Exception as xv:
            self.pyro_daemon.methodcall_error_handler(self.pyro_daemon, self.pyro_client_sock,
                                                      self.pyro_method, self.pyro_vargs, self.pyro_kwars,
                                                      xv)
