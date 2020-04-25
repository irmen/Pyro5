"""
Client related classes (Proxy, mostly)

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import time
import logging
import serpent
import contextlib
from . import config, core, serializers, protocol, errors, socketutil
from .callcontext import current_context
try:
    from greenlet import getcurrent as get_ident
except ImportError:
    from threading import get_ident


log = logging.getLogger("Pyro5.client")

__all__ = ["Proxy", "BatchProxy", "SerializedBlob"]


class Proxy(object):
    """
    Pyro proxy for a remote object. Intercepts method calls and dispatches them to the remote object.

    .. automethod:: _pyroBind
    .. automethod:: _pyroRelease
    .. automethod:: _pyroReconnect
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
         "_pyroRawWireResponse", "_pyroHandshake", "_pyroMaxRetries", "_pyroSerializer",
         "_Proxy__pyroTimeout", "_Proxy__pyroOwnerThread"])

    def __init__(self, uri, connected_socket=None):
        if connected_socket:
            uri = core.URI("PYRO:" + uri + "@<<connected-socket>>:0")
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
        self._pyroHandshake = "hello"  # the data object that should be sent in the initial connection handshake message
        self._pyroMaxRetries = config.MAX_RETRIES
        self.__pyroTimeout = config.COMMTIMEOUT
        self.__pyroOwnerThread = get_ident()     # the thread that owns this proxy
        if config.SERIALIZER not in serializers.serializers:
            raise ValueError("unknown serializer configured")
        # note: we're not clearing the client annotations dict here.
        #       that is because otherwise it will be wiped if a new proxy is needed to connect PYRONAME uris.
        #       clearing the response annotations is okay.
        current_context.response_annotations = {}
        if connected_socket:
            self.__pyroCreateConnection(False, connected_socket)

    def __del__(self):
        if hasattr(self, "_pyroConnection"):
            try:
                self._pyroRelease()
            except Exception:
                pass

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
        if self._pyroConnection:
            connected = "connected " + self._pyroConnection.family()
        else:
            connected = "not connected"
        return "<%s.%s at 0x%x; %s; for %s; owner %s>" % (self.__class__.__module__, self.__class__.__name__,
                                                          id(self), connected, self._pyroUri, self.__pyroOwnerThread)

    def __getstate__(self):
        # make sure a tuple of just primitive types are used to allow for proper serialization
        return str(self._pyroUri), tuple(self._pyroOneway), tuple(self._pyroMethods), \
               tuple(self._pyroAttrs), self._pyroHandshake, self._pyroSerializer

    def __setstate__(self, state):
        self._pyroUri = core.URI(state[0])
        self._pyroOneway = set(state[1])
        self._pyroMethods = set(state[2])
        self._pyroAttrs = set(state[3])
        self._pyroHandshake = state[4]
        self._pyroSerializer = state[5]
        self.__pyroTimeout = config.COMMTIMEOUT
        self._pyroMaxRetries = config.MAX_RETRIES
        self._pyroConnection = None
        self._pyroSeq = 0
        self._pyroRawWireResponse = False
        self.__pyroOwnerThread = get_ident()

    def __copy__(self):
        p = object.__new__(type(self))
        p.__setstate__(self.__getstate__())
        p._pyroTimeout = self._pyroTimeout
        p._pyroRawWireResponse = self._pyroRawWireResponse
        p._pyroMaxRetries = self._pyroMaxRetries
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
        self.__check_owner()
        if self._pyroConnection is not None:
            self._pyroConnection.close()
            self._pyroConnection = None

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
        self.__check_owner()
        current_context.response_annotations = {}
        if self._pyroConnection is None:
            self.__pyroCreateConnection()
        serializer = serializers.serializers[self._pyroSerializer or config.SERIALIZER]
        objectId = objectId or self._pyroConnection.objectId
        annotations = current_context.annotations
        if vargs and isinstance(vargs[0], SerializedBlob):
            # special serialization of a 'blob' that stays serialized
            data, flags = self.__serializeBlobArgs(vargs, kwargs, annotations, flags, objectId, methodname, serializer)
        else:
            # normal serialization of the remote call
            data = serializer.dumpsCall(objectId, methodname, vargs, kwargs)
        if methodname in self._pyroOneway:
            flags |= protocol.FLAGS_ONEWAY
        self._pyroSeq = (self._pyroSeq + 1) & 0xffff
        msg = protocol.SendingMessage(protocol.MSG_INVOKE, flags, self._pyroSeq, serializer.serializer_id, data, annotations=annotations)
        if config.LOGWIRE:
            protocol.log_wiredata(log, "proxy wiredata sending", msg)
        try:
            self._pyroConnection.send(msg.data)
            del msg  # invite GC to collect the object, don't wait for out-of-scope
            if flags & protocol.FLAGS_ONEWAY:
                return None  # oneway call, no response data
            else:
                msg = protocol.recv_stub(self._pyroConnection, [protocol.MSG_RESULT])
                if config.LOGWIRE:
                    protocol.log_wiredata(log, "proxy wiredata received", msg)
                self.__pyroCheckSequence(msg.seq)
                if msg.serializer_id != serializer.serializer_id:
                    error = "invalid serializer in response: %d" % msg.serializer_id
                    log.error(error)
                    raise errors.SerializeError(error)
                if msg.annotations:
                    current_context.response_annotations = msg.annotations
                if self._pyroRawWireResponse:
                    return msg
                data = serializer.loads(msg.data)
                if msg.flags & protocol.FLAGS_ITEMSTREAMRESULT:
                    streamId = bytes(msg.annotations.get("STRM", b"")).decode()
                    if not streamId:
                        raise errors.ProtocolError("result of call is an iterator, but the server is not configured to allow streaming")
                    return _StreamResultIterator(streamId, self)
                if msg.flags & protocol.FLAGS_EXCEPTION:
                    raise data  # if you see this in your traceback, you should probably inspect the remote traceback as well
                else:
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

    def __pyroCreateConnection(self, replaceUri=False, connected_socket=None):
        """
        Connects this proxy to the remote Pyro daemon. Does connection handshake.
        Returns true if a new connection was made, false if an existing one was already present.
        """
        def connect_and_handshake(conn):
            try:
                if self._pyroConnection is not None:
                    return False  # already connected
                if config.SSL:
                    sslContext = socketutil.get_ssl_context(clientcert=config.SSL_CLIENTCERT,
                                                            clientkey=config.SSL_CLIENTKEY,
                                                            keypassword=config.SSL_CLIENTKEYPASSWD,
                                                            cacerts=config.SSL_CACERTS)
                else:
                    sslContext = None
                sock = socketutil.create_socket(connect=connect_location,
                                                reuseaddr=config.SOCK_REUSE,
                                                timeout=self.__pyroTimeout,
                                                nodelay=config.SOCK_NODELAY,
                                                sslContext=sslContext)
                conn = socketutil.SocketConnection(sock, uri.object)
                # Do handshake.
                serializer = serializers.serializers[self._pyroSerializer or config.SERIALIZER]
                data = {"handshake": self._pyroHandshake, "object": uri.object}
                data = serializer.dumps(data)
                msg = protocol.SendingMessage(protocol.MSG_CONNECT, 0, self._pyroSeq, serializer.serializer_id,
                                              data, annotations=current_context.annotations)
                if config.LOGWIRE:
                    protocol.log_wiredata(log, "proxy connect sending", msg)
                conn.send(msg.data)
                msg = protocol.recv_stub(conn, [protocol.MSG_CONNECTOK, protocol.MSG_CONNECTFAIL])
                if config.LOGWIRE:
                    protocol.log_wiredata(log, "proxy connect response received", msg)
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
                    log.debug("connected to %s - %s - %s", self._pyroUri, conn.family(), "SSL" if sslContext else "unencrypted")
                    if msg.annotations:
                        current_context.response_annotations = msg.annotations
                else:
                    conn.close()
                    err = "cannot connect to %s: invalid msg type %d received" % (connect_location, msg.type)
                    log.error(err)
                    raise errors.ProtocolError(err)

        self.__check_owner()
        if self._pyroConnection is not None:
            return False  # already connected
        uri = core.resolve(self._pyroUri)
        # socket connection (normal or Unix domain socket)
        conn = None
        log.debug("connecting to %s", uri)
        connect_location = uri.sockname or (uri.host, uri.port)
        if connected_socket:
            self._pyroConnection = socketutil.SocketConnection(connected_socket, uri.object, True)
        else:
            connect_and_handshake(conn)
        # obtain metadata if this feature is enabled, and the metadata is not known yet
        if not self._pyroMethods and not self._pyroAttrs:
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
            log.debug("from meta: methods=%s, oneway methods=%s, attributes=%s",
                      sorted(self._pyroMethods), sorted(self._pyroOneway), sorted(self._pyroAttrs))
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

    def _pyroInvokeBatch(self, calls, oneway=False):
        flags = protocol.FLAGS_BATCH
        if oneway:
            flags |= protocol.FLAGS_ONEWAY
        return self._pyroInvoke("<batch>", calls, None, flags)

    def _pyroValidateHandshake(self, response):
        """
        Process and validate the initial connection handshake response data received from the daemon.
        Simply return without error if everything is ok.
        Raise an exception if something is wrong and the connection should not be made.
        """
        return

    def _pyroClaimOwnership(self):
        """
        The current thread claims the ownership of this proxy from another thread.
        Any existing connection will remain active!
        """
        if get_ident() != self.__pyroOwnerThread:
            # if self._pyroConnection is not None:
            #     self._pyroConnection.close()
            #     self._pyroConnection = None
            self.__pyroOwnerThread = get_ident()

    def __serializeBlobArgs(self, vargs, kwargs, annotations, flags, objectId, methodname, serializer):
        """
        Special handling of a "blob" argument that has to stay serialized until explicitly deserialized in client code.
        This makes efficient, transparent gateways or dispatchers and such possible:
        they don't have to de/reserialize the message and are independent from the serialized class definitions.
        Annotations are passed in because some blob metadata is added. They're not part of the blob itself.
        """
        if len(vargs) > 1 or kwargs:
            raise errors.SerializeError("if SerializedBlob is used, it must be the only argument")
        blob = vargs[0]
        flags |= protocol.FLAGS_KEEPSERIALIZED
        # Pass the objectId and methodname separately in an annotation because currently,
        # they are embedded inside the serialized message data. And we're not deserializing that,
        # so we have to have another means of knowing the object and method it is meant for...
        # A better solution is perhaps to split the actual remote method arguments from the
        # control data (object + methodname) but that requires a major protocol change.
        # The code below is not as nice but it works without any protocol change and doesn't
        # require a hack either - so it's actually not bad like this.
        import marshal
        annotations["BLBI"] = marshal.dumps((blob.info, objectId, methodname))
        if blob._contains_blob:
            # directly pass through the already serialized msg data from within the blob
            protocol_msg = blob._data
            return protocol_msg.data, flags
        else:
            # replaces SerializedBlob argument with the data to be serialized
            return serializer.dumpsCall(objectId, methodname, blob._data, kwargs), flags

    def __check_owner(self):
        if get_ident() != self.__pyroOwnerThread:
            raise errors.PyroError("the calling thread is not the owner of this proxy, "
                                   "create a new proxy in this thread or transfer ownership.")


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
        self.pyroseq = proxy._pyroSeq

    def __iter__(self):
        return self

    def __next__(self):
        if self.proxy is None:
            raise StopIteration
        if self.proxy._pyroConnection is None:
            raise errors.ConnectionClosedError("the proxy for this stream result has been closed")
        self.pyroseq += 1
        try:
            return self.proxy._pyroInvoke("get_next_stream_item", [self.streamId], {}, objectId=core.DAEMON_NAME)
        except (StopIteration, GeneratorExit):
            # when the iterator is exhausted, the proxy is removed to avoid unneeded close_stream calls later
            # (the server has closed its part of the stream by itself already)
            self.proxy = None
            raise

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def close(self):
        if self.proxy and self.proxy._pyroConnection is not None:
            if self.pyroseq == self.proxy._pyroSeq:
                # we're still in sync, it's okay to use the same proxy to close this stream
                self.proxy._pyroInvoke("close_stream", [self.streamId], {},
                                       flags=protocol.FLAGS_ONEWAY, objectId=core.DAEMON_NAME)
            else:
                # The proxy's sequence number has diverged.
                # One of the reasons this can happen is because this call is being done from python's GC where
                # it decides to gc old iterator objects *during a new call on the proxy*.
                # If we use the same proxy and do a call in between, the other call on the proxy will get an out of sync seq and crash!
                # We create a temporary second proxy to call close_stream on. This is inefficient, but avoids the problem.
                with contextlib.suppress(errors.CommunicationError):
                    with self.proxy.__copy__() as closingProxy:
                        closingProxy._pyroInvoke("close_stream", [self.streamId], {},
                                                 flags=protocol.FLAGS_ONEWAY, objectId=core.DAEMON_NAME)
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

    def __init__(self, proxy):
        self.__proxy = proxy
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

    def __call__(self, oneway=False):
        self.__proxy._pyroClaimOwnership()
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
    This makes efficient, transparent gateways or dispatchers and such possible:
    they don't have to de/reserialize the message and are independent from the serialized class definitions.
    You have to pass this as the only parameter to a remote method call for Pyro to understand it.
    Init arguments:
    ``info`` = some (small) descriptive data about the blob. Can be a simple id or name or guid. Must be marshallable.
    ``data`` = the actual client data payload that you want to transfer in the blob. Can be anything that you would
    otherwise have used as regular remote call arguments.
    """
    def __init__(self, info, data, is_blob=False):
        self.info = info
        self._data = data
        self._contains_blob = is_blob
        if is_blob and not isinstance(data, (protocol.SendingMessage, protocol.ReceivingMessage)):
            raise TypeError("data should be a protocol message object if is_blob is true")

    def deserialized(self):
        """Retrieves the client data stored in this blob. Deserializes the data automatically if required."""
        if self._contains_blob:
            protocol_msg = self._data
            serializer = serializers.serializers_by_id[protocol_msg.serializer_id]
            if isinstance(protocol_msg, protocol.ReceivingMessage):
                _, _, data, _ = serializer.loads(protocol_msg.data)
            else:
                # strip off header bytes from SendingMessage
                payload_data = memoryview(protocol_msg.data)[protocol._header_size:]
                _, _, data, _ = serializer.loads(payload_data)
            return data
        else:
            return self._data


# register the special serializers for the pyro objects
serpent.register_class(Proxy, serializers.pyro_class_serpent_serializer)
serializers.SerializerBase.register_class_to_dict(Proxy, serializers.serialize_pyro_object_to_dict, serpent_too=False)
