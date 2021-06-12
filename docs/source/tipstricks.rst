.. index:: Tips & trics

.. _tipstricks:

*************
Tips & Tricks
*************

.. index:: Best practices

Best practices
==============


Make as little as possible remotely accessible.
-----------------------------------------------

Try to avoid simply sticking an ``@expose`` on the whole class. Instead only mark the methods that you really
want to be remotely accessible. Alternatively, make sure the exposed class only consists of methods
that are okay to be accessed remotely.


Avoid circular communication topologies.
----------------------------------------

When you can have a circular communication pattern in your system (A-->B-->C-->A) this has the potential to deadlock.
You should try to avoid circularity.
Possible ways to break a cycle are to use a oneway call somewhere in the chain or set an ``COMMTIMEOUT``
so that after a certain period in a locking situation the caller aborts with a TimeoutError, effectively breaking the deadlock.


.. index:: releasing a proxy
.. _tipstricks_release_proxy:

Release proxies when no longer used. Avoids 'After X simultaneous proxy connections, Pyro seems to freeze!'
-----------------------------------------------------------------------------------------------------------

A connected proxy that is unused takes up resources on the server. In the case of the threadpool server type,
it locks to a single thread. If you have too many connected proxies at the same time, the server runs out
of threads and can't accept new connections.

You can use the ``THREADPOOL_SIZE`` config item to increase the maximum number of threads that Pyro will use.
Or use the multiplex server instead, which doesn't have this limitation.

To free resources in a timely manner, close (release) proxies that your program no longer needs.
Pyro wil auto-reconnect a proxy when it is used again later.
The easiest way is to use a proxy as a context manager. You can also use an explicit ``_pyroRelease`` call on the proxy.
Releasing and then reconnecting a proxy is very costly so make sure you're not doing this too often.


.. index:: binary blob
    seealso: binary blob; binary data transfer

Avoid large binary blobs over the wire.
---------------------------------------
Pyro is not designed to efficiently transfer large amounts of binary data over the network.
Try to find another protocol that better suits this requirement if you do this regularly.

There are a few tricks to speed up transfer of large blocks of data using Pyro,
read :ref:`binarytransfer` for details about that.


.. index:: object graphs

Minimize object structures that travel over the wire.
-----------------------------------------------------
Pyro serializes the whole object structure you're passing, even when only a fraction
of it is used on the receiving end. It may be necessary to define special lightweight objects
for your Pyro interfaces that hold just the data you need, rather than passing a huge object structure.
It's good design practice anyway to have an "external API" that is different from your internal code,
and tuned for minimal communication overhead or complexity.

This also ties in with just exposing the methods of your server object that should be remotely
accessible, and using primitive types in the interfaces as much as possible to avoid serialization problems.


Consider using basic data types instead of custom classes.
----------------------------------------------------------
Because Pyro serializes the objects you're passing, it needs to know how to serialize custom types.
While you can teach Pyro about these (see :ref:`customizing-serialization`) it may sometimes be easier to just use a builtin datatype instead.
For instance if you have a custom class whose state essentially is a set of numbers, consider then
that it may be easier to just transfer a ``set`` or a ``list`` of those numbers rather than an instance of your
custom class.  It depends on your class and data of course, and whether the receiving code expects
just the list of numbers or really needs an instance of your custom class.



.. index:: Logging

.. _logging:

Logging
=======
If you configure it (see :ref:`config-items`) Pyro will write a bit of debug information, errors, and notifications to a log file.
It uses Python's standard :py:mod:`logging` module for this.
Once enabled, your own program code could use Pyro's logging setup as well.
But if you want to configure your own logging, you have to do this before importing Pyro.

A little example to enable logging by setting the required environment variables from the shell::

    $ export PYRO_LOGFILE=pyro.log
    $ export PYRO_LOGLEVEL=DEBUG
    $ python my_pyro_program.py

Another way is by modifiying ``os.environ`` from within your code itself, *before* any import of Pyro is done::

    import os
    os.environ["PYRO_LOGFILE"] = "pyro.log"
    os.environ["PYRO_LOGLEVEL"] = "DEBUG"

    import Pyro5.api
    # do stuff...

Finally, it is possible to initialize the logging by means of the standard Python ``logging`` module only, but
then you still have to tell Pyro what log level it should use (or it won't log anything)::

    import logging
    logging.basicConfig()  # or your own sophisticated setup
    logging.getLogger("Pyro5").setLevel(logging.DEBUG)
    logging.getLogger("Pyro5.core").setLevel(logging.DEBUG)
    # ... set level of other logger names as desired ...

    import Pyro5.api
    # do stuff...

The various logger names are similar to the module that uses the logger,
so for instance logging done by code in ``Pyro5.core`` will use a logger category name of ``Pyro5.core``.
Look at the top of the source code of the various modules from Pyro to see what the exact names are.


.. index:: multiple NICs, network interfaces

Multiple network interfaces
===========================
This is a difficult subject but here are a few short notes about it.
*At this time, Pyro doesn't support running on multiple network interfaces at the same time*.
You can bind a deamon on INADDR_ANY (0.0.0.0) though, including the name server.
But weird things happen with the URIs of objects published through these servers, because they
will point to 0.0.0.0 and your clients won't be able to connect to the actual objects.

The name server however contains a little trick. The broadcast responder can also be bound on 0.0.0.0
and it will in fact try to determine the correct ip address of the interface that a client needs to use
to contact the name server on. So while you cannot run Pyro daemons on 0.0.0.0 (to respond to requests
from all possible interfaces), sometimes it is possible to run only the name server on 0.0.0.0.
Success of this depends on your particular network setup.


.. index:: wire protocol version

.. _wireprotocol:

Wire protocol version
=====================

Here is a little tip to find out what wire protocol version a given Pyro server is using.
This could be useful if you are getting ``ProtocolError`` about invliad protocol version.

**Server**

This is a way to figure out the protocol version number a given Pyro server is using:
by reading the first 6 bytes from the server socket connection.
The Pyro daemon will respond with a 4-byte string "``PYRO``" followed by a 2-byte number
that is the protocol version used::

    $ nc <pyroservername> <pyroserverport> </dev/zero | od -N 6 -t x1c
    0000000  50  59  52  4f  01  f6
              P   Y   R   O 001 366

This one is talking protocol version ``01 f6`` (502).


**Client**

To find out the protocol version that your client code is using, you can use this::

    $ python -c "import Pyro5.protocol as p; print(p.PROTOCOL_VERSION)"



.. index:: DNS


.. index:: NAT, router, firewall

.. _nat-router:

Pyro behind a NAT router/firewall
=================================
You can run Pyro behind a NAT router/firewall.
Assume the external hostname is 'pyro.server.com' and the external port is 5555.
Also assume the internal host is 'server1.lan' and the internal port is 9999.
You'll need to have a NAT rule that maps pyro.server.com:5555 to server1.lan:9999.
You'll need to start your Pyro daemon, where you specify the ``nathost`` and ``natport`` arguments,
so that Pyro knows it needs to 'publish' URIs containing that *external* location instead of just
using the internal addresses::

    # running on server1.lan
    d = Pyro5.api.Daemon(port=9999, nathost="pyro.server.com", natport=5555)
    uri = d.register(Something, "thing")
    print(uri)     # "PYRO:thing@pyro.server.com:5555"

As you see, the URI now contains the external address.

:py:meth:`Pyro5.server.Daemon.uriFor` by default returns URIs with a NAT address in it (if ``nathost``
and ``natport`` were used). You can override this by setting ``nat=False``::

    # d = Pyro5.api.Daemon(...)
    print(d.uriFor("thing"))                # "PYRO:thing@pyro.server.com:5555"
    print(d.uriFor("thing", nat=False))     # "PYRO:thing@localhost:36124"
    uri2 = d.uriFor(uri.object, nat=False)  # get non-natted uri

The Name server can also be started behind a NAT: it has a couple of command line options that
allow you to specify a nathost and natport for it. See :ref:`nameserver-nameserver`.

.. note::
    The broadcast responder always returns the internal address, never the external NAT address.
    Also, the name server itself won't translate any URIs that are registered with it.
    So if you want it to publish URIs with 'external' locations in them, you have to tell
    the Daemon that registers these URIs to use the correct nathost and natport as well.

.. note::
    In some situations the NAT simply is configured to pass through any port one-to-one to another
    host behind the NAT router/firewall. Pyro facilitates this by allowing you to set the natport
    to 0, in which case Pyro will replace it by the internal port number.



.. index:: failed to locate the nameserver, connection refused

'Failed to locate the nameserver' or 'Connection refused' error, what now?
==========================================================================

Usually when you get an error like "failed to locate the name server" or "connection refused" it is because
there is a configuration problem in your network setup, such as a firewall blocking certain network connections.
Sometimes it can be because you configured Pyro wrong. A checklist to follow to diagnose your issue can be as follows:

- is the name server on a network interface that is visible on the network? If it's on localhost, then it's definitely not! (check the URI)
- is the Pyro object's daemon on a network interface that is visible on the network? If it's on localhost, then it's definitely not! (check the URI)
- with what URI is the Pyro object registered in the Name server? See previous item.
- can you ping the server from your client machine?
- can you telnet to the given host+port from your client machine?
- dealing with IPV4 versus IPV6: do both client and server use the same protocol?
- is the server's ip address as shown one of an externally reachable network interface?
- do you have your server behind a NAT router? See :ref:`nat-router`.
- do you have a firewall or packetfilter running that prevents the connection?
- do you have the same Pyro versions on both server and client?
- what does the pyro logfiles tell you (enable it via the config items on both the server and the client, including the name server. See :ref:`logging`.
- (if not using the default:) do you have a compatible serializer configuration?
- can you obtain a few bytes from the wire using netcat, see :ref:`wireprotocol`.


.. index:: binary data transfer, file transfer

.. _binarytransfer:

Binary data transfer / file transfer
====================================

.. sidebar:: Using Pyro for large data transfers

    At the end of this paragraph, a few alternative approaches of reasonably efficient binary data transfer
    are presented, where most of the code still uses just Pyro's high level abstractions.

Pyro wasn't designed to transfer large amounts of binary data (images, sound files, video clips):
the protocol is not optimized for these kinds of data. The occasional transmission of such data
is fine but if you're dealing with a lot of them or with big files,
it is usually better to use something else to do the actual data transfer (file share+file copy, ftp, http, scp, rsync).

If you find that the default serializer (serpent) is slowing down your data transfer too much,
you could simply try switching to the 'marshal' serializer. It is faster (but supports less types).

.. sidebar:: Numpy arrays and Pyro

    Numpy data types usually cannot be transferred directly, see :ref:`numpy` for more info.

Pyro has a 1 gigabyte message size limitation.  You can avoid hitting this limit by using
the remote iterator feature (return chunks via an iterator or generator function and consume them
on demand in your client).


.. note:: **About the Serpent serializer and binary data:**
    If you transfer binary data using the serpent serializer, be aware that
    its serialization protocol is text based so it has to encode binary data. By default, it uses base-64 to do that.
    This means on the receiving side, instead of the raw bytes, you get a little dictionary
    like this instead: ``{'data': 'aXJtZW4gZGUgam9uZw==', 'encoding': 'base64'}``
    Your client code needs to be explicitly aware of this and to get the original binary data back,
    it has to base-64 decode the data element by itself.  The easiest way to do this is using the
    ``serpent.tobytes`` helper function from the ``serpent`` library, which will convert
    the result to actual bytes if needed, and leave it untouched if it is already in bytes form.

    You can tell the serpent serializer to use Python's repr format for bytes types instead by
    setting the ``SERPENT_BYTES_REPR`` config item to True. Do this for the code that is *serializing*
    the bytes. Serpent (or rather, the safe eval function it uses) will automatically convert this format back to the actual bytes type when deserializing it.
    This is more convenient than the default base-64 representation, but it is also less efficient
    (slower and takes more memory).  This feature is new since Pyro 5.13 and requires Serpent library 1.40 or newer.


The following table is an indication of the relative speeds when dealing with large amounts
of binary data. It lists the results of the :file:`hugetransfer` example, using python 3.8,
over a 1 Gbit LAN connection:

========== ========== ============= ================ ====================
serializer str mb/sec bytes mb/sec  bytearray mb/sec bytearray w/iterator
========== ========== ============= ================ ====================
marshal    95.7       97.1          98.4             55.4
serpent    41.0       23.2          24.3             22.3
json       48.1       not supported not supported    not supported
========== ========== ============= ================ ====================

The json serializer only works with strings, it can't serialize binary data at all.
The serpent serializer can, but read the note above about why it's quite inefficent there.
Marshal is very efficient and is almost saturating the 1 Gbit connection speed limit.


**Alternative: avoid most of the serialization overhead by using annotations**

Pyro allows you to add custom annotation chunks to the request and response messages
(see  :ref:`msg_annotations`). Because these are binary chunks they will not be passed
through the serializer at all. Depending on what the configured maximum message size is
you may have to split up larger files. The ``filetransfer`` example contains
fully working example code to see this in action. It combines this with the remote
iterator capability of Pyro to easily get all chunks of the file.
It has to split up the file in small chunks but is still quite a bit faster than transmitting
bytes through regular response values as bytes or arrays. Also it is using only regular Pyro high level logic
and no low level network or socket code.


**Alternative: integrating raw socket transfer in a Pyro server**

It is possible to get data transfer speeds that are close to the limit of your network adapter
by doing the actual data transfer via low-level socket code and everything else via Pyro.
This keeps the amount of low-level code to a minimum.
Have a look at the ``filetransfer`` example again, to see a possible way of doing this.
It creates a special Daemon subclass that uses Pyro for everything as usual,
but for actual file transfer it sets up a dedicated temporary socket connection over which the file data
is transmitted.


.. index:: IPv6

IPV6 support
============
Pyro supports IPv6. You can use IPv6 addresses (enclosed in brackets) in the same places where you would
normally have used IPv4 addresses. There's one exception: the address notation in a Pyro URI. For example:

``PYRO:objectname@[::1]:3456``

this points at a Pyro object located on the IPv6 "::1" address (localhost). When Pyro displays a numeric
IPv6 location from an URI it will also use the bracket notation. This bracket notation is only used
in Pyro URIs, everywhere else you just type the IPv6 address without brackets.

To tell Pyro to prefer using IPv6 you can use the ``PREFER_IP_VERSION`` config item. It is set to 0 by default,
which means that your operating system is selecting the preferred protocol. Often this is ipv6 if it is
available, but not always, so you can force it by setting this config item to 6 (or 4, if you want ipv4)


.. index:: Numpy, numpy.ndarray
.. _numpy:

Pyro and Numpy
==============
Pyro doesn't support Numpy out of the box. You'll see certain errors occur when
trying to use numpy objects (ndarrays, etcetera) with Pyro::

    TypeError: array([1, 2, 3]) is not JSON serializable
      or
    TypeError: don't know how to serialize class <type 'numpy.ndarray'>
      or
    TypeError: don't know how to serialize class <class 'numpy.int64'>
      or similar.

These errors are caused by Numpy datatypes not being recognised by Pyro's serializer. Why is this:

#. numpy is a third party library and there are many, many others. It is not Pyro's responsibility to understand all of them.
#. numpy is often used in scenarios with large amounts of data. Sending these large arrays over the wire through Pyro
   is often not the best solution. It is not useful to provide transparent support for numpy types
   when you'll be running into trouble often such as slow calls and large network overhead.
#. Pyrolite (:doc:`pyrolite`) would have to get numpy support as well and that is a lot of work (because every numpy type
   would require a mapping to the appropriate Java or .NET type)


If you still want to use numpy with Pyro, you'll have to convert the data to standard Python datatypes before using them in Pyro.
So instead of just ``na = numpy.array(...); return na;``, use this instead:  ``return na.tolist()``.
Or perhaps even ``return array.array('i', na)`` (serpent understands ``array.array`` just fine).
Note that the elements of a numpy array usually are of a special numpy datatype as well (such as ``numpy.int32``).
If you don't convert these individually as well, you will still get serialization errors. That is why something like
``list(na)`` doesn't work: it seems to return a regular python list but the elements are still numpy datatypes.
You have to use the full conversions as mentioned earlier.
Note that you'll have to do a bit more work to deal with multi-dimensional arrays: you have to convert
the shape of the array separately.


.. index::
    double: HTTP gateway server; command line
.. _http-gateway:

Pyro via HTTP and JSON
======================

.. sidebar:: advanced topic

    This is an advanced/low-level Pyro topic.

Pyro provides a HTTP gateway server that translates HTTP requests into Pyro calls. It responds with JSON messages.
This allows clients (including web browsers) to use a simple http interface to call Pyro objects.
Pyro's JSON serialization format is used so the gateway simply passes the JSON response messages back to the caller.
It also provides a simple web page that shows how stuff works.

*Starting the gateway:*

You can launch the HTTP gateway server conveniently via the command line tool.
Because the gateway is written as a wsgi app, you can also stick it into a wsgi server of your own choice.
Import ``pyro_app`` from ``Pyro5.utils.httpgateway`` to do that (that's the app you need to use).


:command:`python -m Pyro5.utils.httpgateway [options]` (or simply: :command:`pyro5-httpgateway [options]`)

A short explanation of the available options can be printed with the help option:

.. program:: Pyro5.utils.httpgateway

.. option:: -h, --help

   Print a short help message and exit.

Most other options should be self explanatory; you can set the listening host and portname etc.
An important option is the exposed names regex option: this controls what objects are
accessible from the http gateway interface. It defaults to something that won't just expose every
internal object in your system. If you want to toy a bit with the examples provided in the gateway's
web page, you'll have to change the option to something like: ``r'Pyro\.|test\.'`` so that those objects
are exposed. This regex is the same as used when listing objects from the name server, so you can use the
``nsc`` tool to check it (with the listmatching command).


*Using the gateway:*

You request the url ``http://localhost:8080/pyro/<<objectname>>/<<method>>`` to invoke a method on the
object with the given name (yes, every call goes through a naming server lookup).
Parameters are passed via a regular query string parameter list (in case of a GET request) or via form post parameters
(in case of a POST request). The response is a JSON document.
In case of an exception, a JSON encoded exception object is returned.
You can easily call this from your web page scripts using ``XMLHttpRequest`` or something like JQuery's ``$.ajax()``.
Have a look at the page source of the gateway's web page to see how this could be done.
Note that you have to comply with the browser's same-origin policy: if you want to allow your own scripts
to access the gateway, you'll have to make sure they are loaded from the same website.

The http gateway server is *stateless* at the moment. This means every call you do will end be processed by
a new Pyro proxy in the gateway server. This is not impacting your client code though, because every call that it
does is also just a stateless http call. It only impacts performance: doing large amounts of calls through
the http gateway will perform much slower as the same calls processed by a native Pyro proxy (which you can instruct
to operate in batch mode as well). However because Pyro is quite efficient, a call through
the gateway is still processed in just a few milliseconds, naming lookup and json serialization all included.

Special http request headers:

- ``X-Pyro-Options``: add this header to the request to set certain pyro options for the call. Possible values (comma-separated):

  - ``oneway``: force the Pyro call to be a oneway call and return immediately.
    The gateway server still returns a 200 OK http response as usual, but the response data is empty.
    This option is to override the semantics for non-oneway method calls if you so desire.

- ``X-Pyro-Gateway-Key``: add this header to the request to set the http gateway key. You can also set it on the request
  with a ``$key=....`` querystring parameter.


Special Http response headers:

-  ``X-Pyro-Correlation-Id``: contains the correlation id Guid that was used for this request/response.


Http response status codes:

- 200 OK: all went well, response is the Pyro response message in JSON serialized format
- 403 Forbidden: you're trying to access an object that is not exposed by configuration
- 404 Not Found: you're requesting a non existing object
- 500 Internal server error: something went wrong during request processing, response is serialized exception object (if available)


Look at the :file:`http` example for working code how you could set this up.


.. index:: current_context, correlation_id
.. _current_context:

Client information on the current_context, correlation id
=========================================================

.. sidebar:: advanced topic

    This is an advanced/low-level Pyro topic.

Pyro provides a *thread-local* object with some information about the current Pyro method call,
such as the client that's performing the call. It is available as :py:data:`Pyro5.current_context`
(shortcut to :py:data:`Pyro5.core.current_context`).
When accessed in a Pyro server it contains various attributes:

.. py:attribute:: Pyro5.current_context.client

    (:py:class:`Pyro5.socketutil.SocketConnection`)
    this is the socket connection with the client that's doing the request.
    You can check the source to see what this is all about, but perhaps the single most useful
    attribute exposed here is ``sock``, which is the socket connection.
    So the client's IP address can for instance be obtained via :code:`Pyro5.current_context.client.sock.getpeername()[0]` .
    However, since for oneway calls the socket connection will likely be closed already, this is not 100% reliable.
    Therefore Pyro stores the result of the ``getpeername`` call in a separate attribute on the context:
    ``client_sock_addr`` (see below)

.. py:attribute:: Pyro5.current_context.client_sock_addr

    (*tuple*) the socket address of the client doing the call. It is a tuple of the client host address and the port.

.. py:attribute:: Pyro5.current_context.seq

    (*int*) request sequence number

.. py:attribute:: Pyro5.current_context.msg_flags

    (*int*) message flags, see :py:class:`Pyro5.message.Message`

.. py:attribute:: Pyro5.current_context.serializer_id

    (*int*) numerical id of the serializer used for this communication, see :py:class:`Pyro5.message.Message` .

.. py:attribute:: Pyro5.current_context.annotations

    (*dict*) message annotations, key is a 4-letter string and the value is a byte sequence.
    Used to send and receive annotations with Pyro requests.
    See :ref:`msg_annotations` for more information about that.

.. py:attribute:: Pyro5.current_context.response_annotations

    (*dict*) message annotations, key is a 4-letter string and the value is a byte sequence.
    Used in client code, the annotations returned by a Pyro server are available here.
    See :ref:`msg_annotations` for more information about that.

.. py:attribute:: Pyro5.current_context.correlation_id

    (:py:class:`uuid.UUID`, optional)  correlation id of the current request / response.
    If you set this (in your client code) before calling a method on a Pyro proxy, Pyro will transfer the
    correlation id to the server context. If the server on their behalf invokes another
    Pyro method, the same correlation id will be passed along. This way it is possible
    to relate all remote method calls that originate from a single call.
    To make this work you'll have to set this to a new :py:class:`uuid.UUID` in your client
    code right before you call a Pyro method.
    Note that it is required that the correlation id is of type :py:class:`uuid.UUID`.
    Note that the HTTP gateway (see :ref:`http-gateway`) also creates a correlation id for
    every request, and will return it via the ``X-Pyro-Correlation-Id`` HTTP-header in the response.
    It will also accept this header optionally on a request in which case it will use the
    value from the header rather than generating a new id.


For an example of how this information can be retrieved, and how to set the ``correlation_id``,
see the :file:`callcontext` example.
See the :file:`usersession` example to learn how you could use it to build user-bound resource access without concurrency problems.


.. index:: resource-tracking
.. _resource_tracking:

Automatically freeing resources when client connection gets closed
==================================================================

.. sidebar:: advanced topic

    This is an advanced/low-level Pyro topic.


A client can call remote methods that allocate stuff in the server.
Normally the client is responsible to call other methods once the resources should be freed.

However if the client forgets this or the connection to the server is forcefully closed before
the client can free the resources, the resources in the server will usually not be freed anymore.

You may be able to solve this in your server code yourself (perhaps using some form of
keepalive/timeout mechanism) but Pyro 4.63 and newer provides a built-in mechanism that can help:
resource tracking on the client connection. Your server will register the resources when they
are allocated, thereby making them tracked resources on the client connection.
These tracked resources will be automatically freed by Pyro if the client connection is closed.

For this to work, the resource object should have a ``close`` method (Pyro will call this).
If needed, you can also override :py:meth:`Pyro5.core.Daemon.clientDisconnect` and do the cleanup
yourself with the ``tracked_resources`` on the connection object.


Resource tracking and untracking is done in your server class on the ``Pyro5.current_context`` object:

.. py:method:: Pyro5.current_context.track_resource(resource)

    Let Pyro track the resource on the current client connection.

.. py:method:: Pyro5.current_context.untrack_resource(resource)

    Untrack a previously tracked resource, useful if you have freed it normally.


See the ``resourcetracking`` example for working code utilizing this.

.. note::
    The order in which the resources are freed is arbitrary.
    Also, if the resource can be garbage collected normally by Python,
    it is removed from the tracked resources. So the ``close`` method should
    not be the only way to properly free such resources (maybe you need a ``__del__`` as well).


.. index:: annotations
.. _msg_annotations:

Message annotations
===================

.. sidebar:: advanced topic

    This is an advanced/low-level Pyro topic.

Pyro's wire protocol allows for a very flexible messaging format by means of *annotations*.
Annotations are extra information chunks that are added to the pyro messages traveling
over the network.

An annotation is a low level datastructure (to optimize the generation of network messages):
a chunk identifier string of exactly 4 characters (such as "CODE"), and its value, a byte sequence.
If you want to put specific data structures into an annotation chunk value, you have to
encode them to a byte sequence yourself (possibly by using one of Pyro's serializers, or any other).
When processing a custom annotation, you have to decode it yourself too.
Communicating annotations with Pyro is done via a normal dictionary of chunk id -> data bytes.
Pyro will take care of encoding this dictionary into the wire message and extracting it out of a response message.

*Adding annotations to messages:*

In client code, you can set the ``annotations`` property of the :py:data:`Pyro5.current_context` object right
before the proxy method call. Pyro will then add that annotations dict to the request message.
In server code, you do this by setting the ``response_annotations``
property of the :py:data:`Pyro5.current_context` in your Pyro object, right before returning the regular response value.
Pyro will add the annotations dict to the response message.

*Using annotations:*

In your client code, you can do that as well, but you should look at the ``response_annotations`` of this context object instead.
If you're using large annotation chunks, it is advised to clear these fields after use.
See :ref:`current_context`.
In your server code, in the Daemon, you can use the :py:data:`Pyro5.current_context` to access the ``annotations`` of the last message that was received.

To see how you can work with custom message annotations, see the :py:mod:`callcontext` or :py:mod:`filetransfer` examples.


.. index:: handshake

.. _conn_handshake:

Connection handshake
====================

.. sidebar:: advanced topic

    This is an advanced/low-level Pyro topic.

When a proxy is first connecting to a Pyro daemon, it exchanges a few messages to set up and validate the connection.
This is called the connection *handshake*. Part of it is the daemon returning the object's metadata (see :ref:`metadata`).
You can hook into this mechanism and influence the data that is initially exchanged during the connection setup,
and you can act on this data. You can disallow the connection based on this, for example.

You can set your own data on the proxy attribute :py:attr:`Pyro5.client.Proxy._pyroHandshake`. You can set any serializable object.
Pyro will send this as the handshake message to the daemon when the proxy tries to connect.
In the daemon, override the method :py:meth:`Pyro5.server.Daemon.validateHandshake` to customize/validate the connection setup.
This method receives the data from the proxy and you can either raise an exception if you don't want to allow the connection,
or return a result value if you are okay with the new connection. The result value again can be any serializable object.
This result value will be received back in the Proxy where you can act on it
if you subclass the proxy and override :py:meth:`Pyro5.client.Proxy._pyroValidateHandshake`.


For an example of how you can work with connections handshake validation, see the :py:mod:`handshake` example.
It implements a (bad!) security mechanism that requires the client to supply a "secret" password to be able to connect to the daemon.


.. index:: dispatcher, gateway

Efficient dispatchers or gateways that don't de/reserialize messages
====================================================================

.. sidebar:: advanced topic

    This is an advanced/low-level Pyro topic.

Imagine you're designing a setup where a Pyro call is essentially dispatched or forwarded
to another server. The dispatcher (sometimes also called gateway) does nothing else than
deciding who the message is for, and then forwarding the Pyro call to the actual object that
performs the operation.

This can be built easily with Pyro by 'intercepting' the call in a dispatcher object,
and performing the remote method call *again* on the actual server object. There's nothing wrong
with this except for perhaps two things:

#. Pyro will deserialize and reserialize the remote method call parameters on every hop, this can
   be quite inefficient if you're dealing with many calls or large argument data structures.

#. The dispatcher object is now dependent on the method call argument data types, because Pyro
   has to be able to de/reserialize them. This often means the dispatcher also needs to have access
   to the same source code files that define the argument data types, that the client and server use.

As long as the dispatcher itself  *doesn't have to know what is even in the actual
message*, Pyro provides a way to avoid both issues mentioned above: use the :py:class:`Pyro5.client.SerializedBlob`.
If you use that as the (single) argument to a remote method call, Pyro will not deserialize the message payload
*until you ask for it* by calling the ``deserialized()`` method on it. Which is something you only do in the
actual server object, and *not* in the dispatcher.
Because the message is then never de/reserialized in the dispatcher code, you avoid the serializer overhead,
and also don't have to include the source code for the serialized types in the dispatcher.
It just deals with a blob of serialized bytes.

An example that shows how this mechanism can be used, can be found as :py:mod:`blob-dispatch` in the examples folder.


.. index:: socketpair, user provided sockets

Hooking onto existing connected sockets such as from socketpair()
=================================================================

For communication between threads or sub-processes, there is ``socket.socketpair()``. It creates
spair of connected sockets that you can share between the threads or processes.
Pyro can use a user-created socket like that, instead of creating
new sockets itself, which means you can use Pyro to talk between threads or sub-processes
over an efficient and isolated channel.
You do this by creating a socket (or a pair) and providing it as the ``connected_socket`` parameter
to the ``Daemon`` and ``Proxy`` classes. For the Daemon, don't pass any other arguments because they
won't be used anyway. For the Proxy, set only the first parameter (``uri``) to just the *name* of the
object in the daemon you want to connect to. So don't use a PYRO or PYRONAME prefix for the uri in this case.

Closing the proxy or the daemon will *not* close the underlying user-supplied socket so you can use it again
for another proxy (to access a different object). You created the socket(s) yourself,
and you also have to close the socket(s) yourself.

See the :py:mod:`socketpair` example for two example programs (one using threads, the other using fork
to create a child process).
