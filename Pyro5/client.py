"""
Client related classes (Proxy etc)

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""


import logging
import time
import threading
import serpent
from . import errors, config, protocol, serializers, socketutil, core


log = logging.getLogger("Pyro5.client")


__all__ = ["Proxy", "BatchProxy", "SerializedBlob"]


class Proxy(object):
    """
    Pyro proxy for a remote object. Intercepts method calls and dispatches them to the remote object.

    .. automethod:: _pyroBind
    .. automethod:: _pyroRelease
    .. automethod:: _pyroReconnect
    .. automethod:: _pyroBatch
    .. automethod:: _pyroAsync
    .. automethod:: _pyroAnnotations
    .. automethod:: _pyroResponseAnnotations
    .. automethod:: _pyroValidateHandshake
    .. autoattribute:: _pyroTimeout
    .. attribute:: _pyroMaxRetries

        Number of retries to perform on communication calls by this proxy, allows you to override the default setting.

    .. attribute:: _pyroSerializer

        Name of the serializer to use by this proxy, allows you to override the default setting.

    .. attribute:: _pyroHandshake

        The data object that should be sent in the initial connection handshake message. Can be any serializable object.
    """
    __pyroAttributes = frozenset(
        ["__getnewargs__", "__getnewargs_ex__", "__getinitargs__", "_pyroConnection", "_pyroUri",
         "_pyroOneway", "_pyroMethods", "_pyroAttrs", "_pyroTimeout", "_pyroSeq",
         "_pyroRawWireResponse", "_pyroHandshake", "_pyroMaxRetries", "_pyroSerializer", "_Proxy__async",
         "_Proxy__pyroTimeout", "_Proxy__pyroConnLock"])

    def __init__(self, uri):
        if isinstance(uri, str):
            uri = core.URI(uri)
        elif not isinstance(uri, core.URI):
            raise TypeError("expected Pyro URI")
        self._pyroUri = uri
        self._pyroConnection = None
        self._pyroSerializer = None  # can be set to the name of a serializer to override the global one per-proxy
        self._pyroMethods = set()  # all methods of the remote object, gotten from meta-data
        self._pyroAttrs = set()  # attributes of the remote object, gotten from meta-data
        self._pyroOneway = set()  # oneway-methods of the remote object, gotten from meta-data
        self._pyroSeq = 0  # message sequence number
        self._pyroRawWireResponse = False  # internal switch to enable wire level responses
        self._pyroHandshake = "hello"  # the data object that should be sent in the initial connection handshake message (can be any serializable object)
        self._pyroMaxRetries = config.MAX_RETRIES
        self.__pyroTimeout = config.COMMTIMEOUT
        self.__pyroConnLock = threading.RLock()
        if config.SERIALIZER not in serializers.serializers:
            raise errors.SerializationError("invalid serializer '{:s}'".format(config.SERIALIZER))
        self.__async = False

    def __del__(self):
        if hasattr(self, "_pyroConnection"):
            self._pyroRelease()

    def __getattr__(self, name):
        if name in Proxy.__pyroAttributes:
            # allows it to be safely pickled
            raise AttributeError(name)
        # get metadata if it's not there yet
        if not self._pyroMethods and not self._pyroAttrs:
            self._pyroGetMetadata()
        if name in self._pyroAttrs:
            return self._pyroInvoke("__getattr__", (name,), None)
        if name not in self._pyroMethods:
            # client side check if the requested attr actually exists
            raise AttributeError("remote object '%s' has no exposed attribute or method '%s'" % (self._pyroUri, name))
        if self.__async:
            raise NotImplementedError()  # XXX
        return _RemoteMethod(self._pyroInvoke, name, self._pyroMaxRetries)

    def __setattr__(self, name, value):
        if name in Proxy.__pyroAttributes:
            return super(Proxy, self).__setattr__(name, value)  # one of the special pyro attributes
        # get metadata if it's not there yet
        if not self._pyroMethods and not self._pyroAttrs:
            self._pyroGetMetadata()
        if name in self._pyroAttrs:
            return self._pyroInvoke("__setattr__", (name, value), None)  # remote attribute
        # client side validation if the requested attr actually exists
        raise AttributeError("remote object '%s' has no exposed attribute '%s'" % (self._pyroUri, name))

    def __repr__(self):
        connected = "connected" if self._pyroConnection else "not connected"
        return "<%s.%s at 0x%x; %s; for %s>" % (self.__class__.__module__, self.__class__.__name__,
                                                id(self), connected, self._pyroUri)

    def __unicode__(self):
        return str(self)

    def __getstate_for_dict__(self):
        # for backwards compatibility reasons we also put the timeout and maxretries into the state
        return self._pyroUri.asString(), tuple(self._pyroOneway), tuple(self._pyroMethods), tuple(self._pyroAttrs),\
            self.__pyroTimeout, self._pyroHandshake, self._pyroMaxRetries, self._pyroSerializer

    def __setstate_from_dict__(self, state):
        uri = core.URI(state[0])
        oneway = set(state[1])
        methods = set(state[2])
        attrs = set(state[3])
        timeout = state[4]
        handshake = state[5]
        max_retries = state[6]
        serializer = None if len(state) < 9 else state[7]
        self.__setstate__((uri, oneway, methods, attrs, timeout, handshake, max_retries, serializer))

    def __getstate__(self):
        # for backwards compatibility reasons we also put the timeout and maxretries into the state
        return self._pyroUri, self._pyroOneway, self._pyroMethods, self._pyroAttrs, self.__pyroTimeout,\
               self._pyroHandshake, self._pyroMaxRetries, self._pyroSerializer

    def __setstate__(self, state):
        # Note that the timeout and maxretries are also part of the state (for backwards compatibility reasons),
        # but we're not using them here. Instead we get the configured values from the 'local' config.
        self._pyroUri, self._pyroOneway, self._pyroMethods, self._pyroAttrs, _, self._pyroHandshake = state[:6]
        self._pyroSerializer = None if len(state) < 9 else state[7]
        self.__pyroTimeout = config.COMMTIMEOUT
        self._pyroMaxRetries = config.MAX_RETRIES
        self._pyroConnection = None
        self._pyroSeq = 0
        self._pyroRawWireResponse = False
        self.__pyroConnLock = threading.RLock()
        self.__async = False

    def __copy__(self):
        uri_copy = core.URI(self._pyroUri)
        p = type(self)(uri_copy)
        p._pyroOneway = set(self._pyroOneway)
        p._pyroMethods = set(self._pyroMethods)
        p._pyroAttrs = set(self._pyroAttrs)
        p._pyroSerializer = self._pyroSerializer
        p._pyroTimeout = self._pyroTimeout
        p._pyroHandshake = self._pyroHandshake
        p._pyroRawWireResponse = self._pyroRawWireResponse
        p._pyroMaxRetries = self._pyroMaxRetries
        p.__async = self.__async
        return p

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._pyroRelease()

    def __eq__(self, other):
        if other is self:
            return True
        return isinstance(other, Proxy) and other._pyroUri == self._pyroUri

    def __ne__(self, other):
        if other and isinstance(other, Proxy):
            return other._pyroUri != self._pyroUri
        return True

    def __hash__(self):
        return hash(self._pyroUri)

    def __dir__(self):
        result = dir(self.__class__) + list(self.__dict__.keys())
        return sorted(set(result) | self._pyroMethods | self._pyroAttrs)

    def _pyroRelease(self):
        """release the connection to the pyro daemon"""
        with self.__pyroConnLock:
            if self._pyroConnection is not None:
                self._pyroConnection.close()
                self._pyroConnection = None
                log.debug("connection released")

    def _pyroBind(self):
        """
        Bind this proxy to the exact object from the uri. That means that the proxy's uri
        will be updated with a direct PYRO uri, if it isn't one yet.
        If the proxy is already bound, it will not bind again.
        """
        return self.__pyroCreateConnection(True)

    def __pyroGetTimeout(self):
        return self.__pyroTimeout

    def __pyroSetTimeout(self, timeout):
        self.__pyroTimeout = timeout
        if self._pyroConnection is not None:
            self._pyroConnection.timeout = timeout

    _pyroTimeout = property(__pyroGetTimeout, __pyroSetTimeout, doc="""
        The timeout in seconds for calls on this proxy. Defaults to ``None``.
        If the timeout expires before the remote method call returns,
        Pyro will raise a :exc:`Pyro5.errors.TimeoutError`""")

    def _pyroInvoke(self, methodname, vargs, kwargs, flags=0, objectId=None):
        """perform the remote method call communication"""
        with self.__pyroConnLock:
            if self._pyroConnection is None:
                # rebind here, don't do it from inside the invoke because deadlock will occur
                self.__pyroCreateConnection()
            serializer = serializers.serializers[self._pyroSerializer or config.SERIALIZER]
            if not serializer:
                raise errors.SerializationError("invalid serializer")
            annotations = self._pyroAnnotations()
            objectId = objectId or self._pyroConnection.objectId
            if vargs and isinstance(vargs[0], SerializedBlob):
                # special serialization of a 'blob' that stays serialized
                raise NotImplementedError  # XXX
            else:
                # normal serialization of the remote call
                data = serializer.dumpsCall(objectId, methodname, vargs, kwargs)
            if methodname in self._pyroOneway:
                flags |= protocol.FLAGS_ONEWAY
            self._pyroSeq = (self._pyroSeq + 1) & 0xffff
            msg = protocol.SendingMessage(protocol.MSG_INVOKE, flags, self._pyroSeq, serializer.serializer_id, data, annotations)
            flags = msg.flags
            if config.LOGWIRE:
                core.log_wiredata(log, "proxy wiredata sending", msg)
            try:
                self._pyroConnection.send(msg.data)
                if flags & protocol.FLAGS_ONEWAY:
                    return None  # oneway call, no response data
                else:
                    msg = protocol.recv_stub(self._pyroConnection, [protocol.MSG_RESULT])
                    if config.LOGWIRE:
                        core.log_wiredata(log, "proxy wiredata received", msg)
                    self.__pyroCheckSequence(msg.seq)
                    if msg.serializer_id != serializer.serializer_id:
                        error = "invalid serializer in response: %d" % msg.serializer_id
                        log.error(error)
                        raise errors.SerializationError(error)
                    if msg.annotations:
                        self._pyroResponseAnnotations(msg.annotations, msg.type)
                    if self._pyroRawWireResponse:
                        msg.decompress_if_needed()
                        return msg
                    data = serializer.loads(msg.data)
                    if msg.flags & protocol.FLAGS_ITEMSTREAMRESULT:
                        streamId = msg.annotations.get("STRM", b"").decode()
                        if not streamId:
                            raise errors.ProtocolError("result of call is an iterator, but the server is not configured to allow streaming")
                        return _StreamResultIterator(streamId, self)
                    if msg.flags & protocol.FLAGS_EXCEPTION:
                        raise data
                    return data
            except (errors.CommunicationError, KeyboardInterrupt):
                # Communication error during read. To avoid corrupt transfers, we close the connection.
                # Otherwise we might receive the previous reply as a result of a new method call!
                # Special case for keyboardinterrupt: people pressing ^C to abort the client
                # may be catching the keyboardinterrupt in their code. We should probably be on the
                # safe side and release the proxy connection in this case too, because they might
                # be reusing the proxy object after catching the exception...
                self._pyroRelease()
                raise

    def __pyroCheckSequence(self, seq):
        if seq != self._pyroSeq:
            err = "invoke: reply sequence out of sync, got %d expected %d" % (seq, self._pyroSeq)
            log.error(err)
            raise errors.ProtocolError(err)

    def __pyroCreateConnection(self, replaceUri=False):
        """
        Connects this proxy to the remote Pyro daemon. Does connection handshake.
        Returns true if a new connection was made, false if an existing one was already present.
        """
        with self.__pyroConnLock:
            if self._pyroConnection is not None:
                return False  # already connected
            from .nameserver import resolve   # not in global scope because of circular import
            uri = resolve(self._pyroUri)
            # socket connection (normal or Unix domain socket)
            conn = None
            log.debug("connecting to %s", uri)
            connect_location = uri.sockname or (uri.host, uri.port)
            try:
                if self._pyroConnection is not None:
                    return False  # already connected
                sock = socketutil.createSocket(connect=connect_location, reuseaddr=config.SOCK_REUSE, timeout=self.__pyroTimeout, nodelay=config.SOCK_NODELAY)
                conn = socketutil.SocketConnection(sock, uri.object)
                # Do handshake.
                serializername = self._pyroSerializer or config.SERIALIZER
                serializer = serializers.serializers.get(serializername)
                if not serializer:
                    raise errors.SerializationError("invalid serializer '{:s}'".format(serializername))
                data = {"handshake": self._pyroHandshake, "object": uri.object}
                msg = protocol.SendingMessage(protocol.MSG_CONNECT, 0, self._pyroSeq, serializer.serializer_id, serializer.dumps(data), self._pyroAnnotations())
                if config.LOGWIRE:
                    core.log_wiredata(log, "proxy connect sending", msg)
                conn.send(msg.data)
                msg = protocol.recv_stub(conn, [protocol.MSG_CONNECTOK, protocol.MSG_CONNECTFAIL])
                if config.LOGWIRE:
                    core.log_wiredata(log, "proxy connect response received", msg)
            except Exception as x:
                if conn:
                    conn.close()
                err = "cannot connect to %s: %s" % (connect_location, x)
                log.error(err)
                if isinstance(x, errors.CommunicationError):
                    raise
                else:
                    raise errors.CommunicationError(err) from x
            else:
                handshake_response = "?"
                if msg.data:
                    serializer = serializers.serializers_by_id[msg.serializer_id]
                    handshake_response = serializer.loads(msg.data)
                if msg.type == protocol.MSG_CONNECTFAIL:
                    error = "connection to %s rejected: %s" % (connect_location, handshake_response)
                    conn.close()
                    log.error(error)
                    raise errors.CommunicationError(error)
                elif msg.type == protocol.MSG_CONNECTOK:
                    self.__processMetadata(handshake_response["meta"])
                    handshake_response = handshake_response["handshake"]
                    self._pyroConnection = conn
                    if replaceUri:
                        self._pyroUri = uri
                    self._pyroValidateHandshake(handshake_response)
                    log.debug("connected to %s", self._pyroUri)
                    if msg.annotations:
                        self._pyroResponseAnnotations(msg.annotations, msg.type)
                else:
                    conn.close()
                    err = "cannot connect to %s: invalid msg type %d received" % (connect_location, msg.type)
                    log.error(err)
                    raise errors.ProtocolError(err)
            # obtain metadata if it is not known yet
            if self._pyroMethods or self._pyroAttrs:
                log.debug("reusing existing metadata")
            else:
                self._pyroGetMetadata(uri.object)
            return True

    def _pyroGetMetadata(self, objectId=None, known_metadata=None):
        """
        Get metadata from server (methods, attrs, oneway, ...) and remember them in some attributes of the proxy.
        Usually this will already be known due to the default behavior of the connect handshake, where the
        connect response also includes the metadata.
        """
        objectId = objectId or self._pyroUri.object
        log.debug("getting metadata for object %s", objectId)
        if self._pyroConnection is None and not known_metadata:
            try:
                self.__pyroCreateConnection()
            except errors.PyroError:
                log.error("problem getting metadata: cannot connect")
                raise
            if self._pyroMethods or self._pyroAttrs:
                return  # metadata has already been retrieved as part of creating the connection
        try:
            # invoke the get_metadata method on the daemon
            result = known_metadata or self._pyroInvoke("get_metadata", [objectId], {}, objectId=core.DAEMON_NAME)
            self.__processMetadata(result)
        except errors.PyroError:
            log.exception("problem getting metadata")
            raise

    def __processMetadata(self, metadata):
        if not metadata:
            return
        self._pyroOneway = set(metadata["oneway"])
        self._pyroMethods = set(metadata["methods"])
        self._pyroAttrs = set(metadata["attrs"])
        if log.isEnabledFor(logging.DEBUG):
            log.debug("from meta: oneway methods=%s", sorted(self._pyroOneway))
            log.debug("from meta: methods=%s", sorted(self._pyroMethods))
            log.debug("from meta: attributes=%s", sorted(self._pyroAttrs))
        if not self._pyroMethods and not self._pyroAttrs:
            raise errors.PyroError("remote object doesn't expose any methods or attributes. Did you forget setting @expose on them?")

    def _pyroReconnect(self, tries=100000000):
        """
        (Re)connect the proxy to the daemon containing the pyro object which the proxy is for.
        In contrast to the _pyroBind method, this one first releases the connection (if the proxy is still connected)
        and retries making a new connection until it succeeds or the given amount of tries ran out.
        """
        self._pyroRelease()
        while tries:
            try:
                self.__pyroCreateConnection()
                return
            except errors.CommunicationError:
                tries -= 1
                if tries:
                    time.sleep(2)
        msg = "failed to reconnect"
        log.error(msg)
        raise errors.ConnectionClosedError(msg)

    def _pyroAsync(self):
        """returns an async version of the proxy so you can do asynchronous method calls"""
        asyncproxy = self.__copy__()
        asyncproxy.__async = True
        return asyncproxy

    def _pyroInvokeBatch(self, calls, oneway=False):
        flags = protocol.FLAGS_BATCH
        if oneway:
            flags |= protocol.FLAGS_ONEWAY
        return self._pyroInvoke("<batch>", calls, None, flags)

    def _pyroAnnotations(self):
        """
        Returns a dict with annotations to be sent with each message.
        Default behavior is to include the correlation id from the current context (if it is set).
        If you override this, don't forget to call the original method and add to the dictionary returned from it,
        rather than simply returning a new dictionary.
        """
        if core.current_context.correlation_id:
            return {"CORR": core.current_context.correlation_id.bytes}
        return {}

    def _pyroResponseAnnotations(self, annotations, msgtype):
        """
        Process any response annotations (dictionary set by the daemon).
        Usually this contains the internal Pyro annotations such as correlation id,
        and if you override the annotations method in the daemon, can contain your own annotations as well.
        """
        pass

    def _pyroValidateHandshake(self, response):
        """
        Process and validate the initial connection handshake response data received from the daemon.
        Simply return without error if everything is ok.
        Raise an exception if something is wrong and the connection should not be made.
        """
        return


class _RemoteMethod(object):
    """method call abstraction"""

    def __init__(self, send, name, max_retries):
        self.__send = send
        self.__name = name
        self.__max_retries = max_retries

    def __getattr__(self, name):
        return _RemoteMethod(self.__send, "%s.%s" % (self.__name, name), self.__max_retries)

    def __call__(self, *args, **kwargs):
        for attempt in range(self.__max_retries + 1):
            try:
                return self.__send(self.__name, args, kwargs)
            except (errors.ConnectionClosedError, errors.TimeoutError):
                # only retry for recoverable network errors
                if attempt >= self.__max_retries:
                    # last attempt, raise the exception
                    raise


class _StreamResultIterator(object):
    """
    Pyro returns this as a result of a remote call which returns an iterator or generator.
    It is a normal iterable and produces elements on demand from the remote iterator.
    You can simply use it in for loops, list comprehensions etc.
    """
    def __init__(self, streamId, proxy):
        self.streamId = streamId
        self.proxy = proxy

    def __iter__(self):
        return self

    def next(self):
        # python 2.x support
        return self.__next__()

    def __next__(self):
        if self.proxy._pyroConnection is None:
            raise errors.ConnectionClosedError("the proxy for this stream result has been closed")
        return self.proxy._pyroInvoke("get_next_stream_item", [self.streamId], {}, objectId=core.DAEMON_NAME)

    def __del__(self):
        self.close()

    def close(self):
        if self.proxy and self.proxy._pyroConnection is not None:
            self.proxy._pyroInvoke("close_stream", [self.streamId], {}, flags=protocol.FLAGS_ONEWAY, objectId=core.DAEMON_NAME)
        self.proxy = None


class _BatchedRemoteMethod(object):
    """method call abstraction that is used with batched calls"""

    def __init__(self, calls, name):
        self.__calls = calls
        self.__name = name

    def __getattr__(self, name):
        return _BatchedRemoteMethod(self.__calls, "%s.%s" % (self.__name, name))

    def __call__(self, *args, **kwargs):
        self.__calls.append((self.__name, args, kwargs))


class BatchProxy(object):
    """Proxy that lets you batch multiple method calls into one.
    It is constructed with a reference to the normal proxy that will
    carry out the batched calls. Call methods on this object that you want to batch,
    and finally call the batch proxy itself. That call will return a generator
    for the results of every method call in the batch (in sequence)."""

    def __init__(self, normalproxy):
        self.__proxy = normalproxy
        self.__calls = []

    def __getattr__(self, name):
        return _BatchedRemoteMethod(self.__calls, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __copy__(self):
        copy = type(self)(self.__proxy)
        copy.__calls = list(self.__calls)
        return copy

    def __resultsgenerator(self, results):
        for result in results:
            if isinstance(result, core._ExceptionWrapper):
                result.raiseIt()  # re-raise the remote exception locally.
            else:
                yield result  # it is a regular result object, yield that and continue.

    def __call__(self, oneway=False, async=False):
        if oneway and async:
            raise errors.PyroError("async oneway calls make no sense")
        if async:
            raise NotImplementedError    # XXX
        else:
            results = self.__proxy._pyroInvokeBatch(self.__calls, oneway)
            self.__calls = []  # clear for re-use
            if not oneway:
                return self.__resultsgenerator(results)

    def _pyroInvoke(self, name, args, kwargs):
        # ignore all parameters, we just need to execute the batch
        results = self.__proxy._pyroInvokeBatch(self.__calls)
        self.__calls = []  # clear for re-use
        return self.__resultsgenerator(results)


class SerializedBlob(object):
    """
    Used to wrap some data to make Pyro pass this object transparently (it keeps the serialized payload as-is)
    Only when you need to access the actual client data you can deserialize on demand.
    This allows for transparent Pyro proxies and dispatchers and such.
    You have to pass this as the only parameter to a remote method call for Pyro to understand it.
    Init arguments:
    ``info`` = some (small) descriptive data about the blob. Can be a simple id or name or guid. Must be marshallable.
    ``data`` = the actual client data payload that you want to transfer in the blob. Can be anything that you would
    otherwise have used as regular remote call arguments.
    """
    def __init__(self, info, data):
        self.info = info
        self._data = data
        self._contains_blob = False

    def deserialized(self):
        """Retrieves the client data stored in this blob. Deserializes the data automatically if required."""
        if self._contains_blob:
            protocol_msg = self._data
            serializer = serializers.serializers_by_id[protocol_msg.serializer_id]
            _, _, data, _ = serializer.loads(protocol_msg.data)
            return data
        else:
            return self._data


# register the special serializers for the pyro objects
serpent.register_class(Proxy, serializers.pyro_class_serpent_serializer)
serializers.SerializerBase.register_class_to_dict(Proxy, serializers.serialize_pyro_object_to_dict, serpent_too=False)
