.. index:: client code, calling remote objects

*******************************
Clients: Calling remote objects
*******************************

This chapter explains how you write code that calls remote objects.
Often, a program that calls methods on a Pyro object is called a *client* program.
(The program that provides the object and actually runs the methods, is the *server*.
Both roles can be mixed in a single program.)

Make sure you are familiar with Pyro's :ref:`keyconcepts` before reading on.


.. index:: object discovery, location, object name

.. _object-discovery:

Object discovery
================

To be able to call methods on a Pyro object, you have to tell Pyro where it can find
the actual object. This is done by creating an appropriate URI, which contains amongst
others the object name and the location where it can be found.
You can create it in a number of ways.


.. index:: PYRO protocol type

* directly use the object name and location.
    This is the easiest way and you write an URI directly like this: ``PYRO:someobjectid@servername:9999``
    It requires that you already know the object id, servername, and port number.
    You could choose to use fixed object names and fixed port numbers to connect Pyro daemons on.
    For instance, you could decide that your music server object is always called "musicserver",
    and is accessible on port 9999 on your server musicbox.my.lan. You could then simply use::

        uri_string = "PYRO:musicserver@musicbox.my.lan:9999"
        # or use Pyro5.api.URI("...") for an URI object instead of a string

    Most examples that come with Pyro simply ask the user to type this in on the command line,
    based on what the server printed. This is not very useful for real programs,
    but it is a simple way to make it work. You could write the information to a file
    and read that from a file share (only slightly more useful, but it's just an idea).

* use a logical name and look it up in the name server.
    A more flexible way of locating your objects is using logical names for them and storing
    those in the Pyro name server. Remember that the name server is like a phone book, you look
    up a name and it gives you the exact location.
    To continue on the previous bullet, this means your clients would only have to know the
    logical name "musicserver". They can then use the name server to obtain the proper URI::

        import Pyro5.api
        nameserver = Pyro5.api.locate_ns()
        uri = nameserver.lookup("musicserver")
        # ... uri now contains the URI with actual location of the musicserver object

    You might wonder how Pyro finds the Name server. This is explained in the separate chapter :doc:`nameserver`.

* use a logical name and let Pyro look it up in the name server for you.
    Very similar to the option above, but even more convenient, is using the *meta*-protocol
    identifier ``PYRONAME`` in your URI string. It lets Pyro know that it should lookup
    the name following it, in the name server. Pyro should then
    use the resulting URI from the name server to contact the actual object.
    See :ref:`nameserver-pyroname`.
    This means you can write::

        uri_string = "PYRONAME:musicserver"
        # or Pyro5.api.URI("PYRONAME:musicserver") for an URI object

    You can use this URI everywhere you would normally use a normal uri (using ``PYRO``).
    Everytime Pyro encounters the ``PYRONAME`` uri it will use the name server automatically
    to look up the object for you. [#pyroname]_

* use object metadata tagging to look it up (yellow-pages style lookup).
    You can do this directly via the name server for maximum control, or use the ``PYROMETA`` protocol type.
    See :ref:`nameserver-pyrometa`. This means you can write::

        uri_string = "PYROMETA:metatag1,metatag2"
        # or Pyro5.api.URI("PYROMETA:metatag1,metatag2") for an URI object

    You can use this URI everywhere you would normally use a normal uri.
    Everytime Pyro encounters the ``PYROMETA`` uri it will use the name server automatically
    to find a random object for you with the given metadata tags. [#pyroname]_

.. [#pyroname] this is not very efficient if it occurs often. Have a look at the :doc:`tipstricks`
   chapter for some hints about this.


.. index::
    double: Proxy; calling methods

Calling methods
===============
Once you have the location of the Pyro object you want to talk to, you create a Proxy for it.
Normally you would perhaps create an instance of a class, and invoke methods on that object.
But with Pyro, your remote method calls on Pyro objects go through a proxy.
The proxy can be treated as if it was the actual object, so you write normal python code
to call the remote methods and deal with the return values, or even exceptions::

    # Continuing our imaginary music server example.
    # Assume that uri contains the uri for the music server object.

    musicserver = Pyro5.api.Proxy(uri)
    try:
        musicserver.load_playlist("90s rock")
        musicserver.play()
        print("Currently playing:", musicserver.current_song())
    except MediaServerException:
        print("Couldn't select playlist or start playing")

For normal usage, there's not a single line of Pyro specific code once you have a proxy!


.. index::
    single: object serialization
    double: serialization; serpent
    double: serialization; marshal
    double: serialization; json
    double: serialization; msgpack


.. index::
    double: Proxy; remote attributes

Accessing remote attributes
===========================
You can access exposed attributes of your remote objects directly via the proxy.
If you try to access an undefined or unexposed attribute, the proxy will raise an AttributeError stating the problem.
Note that direct remote attribute access only works if the metadata feature is enabled (``METADATA`` config item, enabled by default).
::

    import Pyro5.api

    p = Pyro5.api.Proxy("...")
    velo = p.velocity    # attribute access, no method call
    print("velocity = ", velo)


See the :file:`attributes` example for more information.



.. _object-serialization:

Serialization
=============

Pyro will serialize the objects that you pass to the remote methods, so they can be sent across
a network connection. Depending on the serializer that is being used, there will be some limitations
on what objects you can use.

* **serpent**: the default serializer. Serializes into Python literal expressions. Accepts quite a lot of different types.
  Many will be serialized as dicts. You might need to explicitly translate literals back to specific types
  on the receiving end if so desired, because most custom classes aren't dealt with automatically.
  Requires third party library module, but it will be installed automatically as a dependency of Pyro.
* **json**: more restricted as serpent, less types supported. Part of the standard library.
* **marshal**: a very limited but very fast serializer. Can deal with a small range of builtin types only,
  no custom classes can be serialized. Part of the standard library.
* **msgpack**: See https://pypi.python.org/pypi/msgpack Reasonably fast serializer (and a lot faster if you're using the C module extension).
  Can deal with many builtin types, but not all.   Not enabled by default because it's optional,
  but it's safe to add to the accepted serializers config item if you have it installed.

.. index:: SERIALIZER

You select the serializer to be used by setting the ``SERIALIZER`` config item. (See the :doc:`/config` chapter).
The valid choices are the names of the serializer from the list mentioned above.

It is possible to override the serializer on a particular proxy. This allows you to connect to one server
using the default serpent serializer and use another proxy to connect to a different server using the json
serializer, for instance. Set the desired serializer name in ``proxy._pyroSerializer`` to override.

.. index:: deserialization, serializing custom classes, deserializing custom classes

.. _customizing-serialization:

Customizing serialization
-------------------------

By default, custom classes are serialized into a dict.
They are not deserialized back into instances of your custom class. This avoids possible security issues.
An exception to this however are certain classes in the Pyro5 package itself (such as the URI and Proxy classes).
They *are* deserialized back into objects of that certain class, because they are critical for Pyro to function correctly.

There are a few hooks however that allow you to extend this default behaviour and register certain custom
converter functions. These allow you to change the way your custom classes are treated, and allow you
to actually get instances of your custom class back from the deserialization if you so desire.

The hooks are provided via several methods:
    :py:meth:`Pyro5.api.register_class_to_dict` and :py:meth:`Pyro5.api.register_dict_to_class`

and their unregister-counterparts:
    :py:meth:`Pyro5.api.unregister_class_to_dict` and :py:meth:`Pyro5.api.unregister_dict_to_class`

Click on the method link to see its apidoc, or have a look at the :file:`custom-serialization` example and the :file:`test_serialize` unit tests for more information.
It is recommended to avoid using these hooks if possible, there's a security risk
to create arbitrary objects from serialized data that is received from untrusted sources.


.. index:: release proxy connection
.. index::
    double: Proxy; cleaning up
.. _client_cleanup:

Proxies, connections, threads and cleaning up
=============================================
Here are some rules:

* Every single Proxy object will have its own socket connection to the daemon.
* You cannot share Proxy objects among threads. One single thread 'owns' a proxy.  It is possible to explicitly transfer ownership to another thread.
* Usually every connection in the daemon has its own processing thread there, but for more details see the :doc:`servercode` chapter.
* Consider cleaning up a proxy object explicitly if you know you won't be using it again in a while. That will free up resources and socket connections.
  You can do this in two ways:

  1. calling ``_pyroRelease()`` on the proxy.
  2. using the proxy as a context manager in a ``with`` statement. *This is the preferred way of creating and using Pyro proxies.*
     This ensures that when you're done with it, or an error occurs (inside the with-block),
     the connection is released::

        with Pyro5.api.Proxy(".....") as obj:
            obj.method()

  *Note:* you can still use the proxy object when it is disconnected: Pyro will reconnect it for you as soon as it's needed again.
* At proxy creation, no actual connection is made. The proxy is only actually connected at first use, or when you manually
  connect it using the ``_pyroReconnect()`` or ``_pyroBind()`` methods.


.. index::
    double: oneway; client method call

.. _oneway-calls-client:

Oneway calls
============

Normal method calls always block until the response is returned. This can be any normal return value, ``None``,
or an error in the form of a raised exception. The client code execution is suspended until the method call
has finished and produced its result.

Some methods never return any response or you are simply not interested in it (including errors and
exceptions!), or you don't want to wait until the result is available but rather continue immediately.
You can tell Pyro that calls to these methods should be done as *one-way calls*.
For calls to such methods, Pyro will not wait for a response from the remote object.
The return value of these calls is always ``None``, which is returned *immediately* after submitting the method
invocation to the server. The server will process the call while your client continues execution.
The client can't tell if the method call was successful, because no return value, no errors and no exceptions will be returned!
If you want to find out later what - if anything - happened, you have to call another (non-oneway) method that does return a value.

.. index::
    double: @Pyro5.api.oneway; client handling

**How to make methods one-way:**
You mark the methods of your class *in the server* as one-way by using a special *decorator*.
See :ref:`decorating-pyro-class` for details on how to do this.
See the :file:`oneway` example for some code that demonstrates the use of oneway methods.


.. index:: batch calls

.. _batched-calls:

Batched calls
=============
Doing many small remote method calls in sequence has a fair amount of latency and overhead.
Pyro provides a means to gather all these small calls and submit it as a single 'batched call'.
When the server processed them all, you get back all results at once.
Depending on the size of the arguments, the network speed, and the amount of calls,
doing a batched call can be *much* faster than invoking every call by itself.
Note that this feature is only available for calls on the same proxy object.

How it works:

#. You create a batch proxy object for the proxy object.
#. Call all the methods you would normally call on the regular proxy, but use the batch proxy object instead.
#. Call the batch proxy object itself to obtain the generator with the results.

You create a batch proxy using this: ``batch = Pyro5.api.BatchProxy(proxy)``.
The signature of the batch proxy call is as follows:

.. py:method:: batchproxy.__call__([oneway=False])

    Invoke the batch and when done, returns a generator that produces the results of every call, in order.
    If ``oneway==True``, perform the whole batch as one-way calls, and return ``None`` immediately.
    If ``asynchronous==True``, perform the batch asynchronously, and return an asynchronous call result object immediately.

**Simple example**::

    batch = Pyro5.api.BatchProxy(proxy)
    batch.method1()
    batch.method2()
    # more calls ...
    batch.methodN()
    results = batch()   # execute the batch
    for result in results:
        print(result)   # process result in order of calls...

**Oneway batch**::

    results = batch(oneway=True)
    # results==None


See the :py:mod:`batchedcalls` example for more details.


.. index:: remote iterators/generators

Remote iterators/generators
===========================

You can iterate over a remote iterator or generator function as if it
was a perfectly normal Python iterable. Pyro will fetch the items one by one from the server that is
running the remote iterator until all elements have been consumed or the client disconnects.

.. sidebar::
    *Filter on the server*

    If you plan to filter the items that are returned from the iterator,
    it is strongly suggested to do that on the server and not in your client.
    Because otherwise it is possible that you first have
    to serialize and transfer all possible items from the server only to select
    a few out of them, which is very inefficient.

    *Beware of many small items*

    Pyro has to do a remote call to get every next item from the iterable.
    If your iterator produces lots of small individual items, this can be quite
    inefficient (many small network calls). Either chunk them up a bit or
    use larger individual items.


So you can write in your client::

    proxy = Pyro5.api.Proxy("...")
    for item in proxy.things():
        print(item)

The implementation of the ``things`` method can return a normal list but can
also return an iterator or even be a generator function itself. This has the usual benefits of "lazy" generators:
no need to create the full collection upfront which can take a lot of memory, possibility
of infinite sequences, and spreading computation load more evenly.

By default the remote item streaming is enabled in the server and there is no time limit set
for how long iterators and generators can be 'alive' in the server. You can configure this however
if you want to restrict resource usage or disable this feature altogether, via the
``ITER_STREAMING`` and ``ITER_STREAM_LIFETIME`` config items.

Lingering when disconnected: the ``ITER_STREAM_LINGER`` config item controls the number of seconds
a remote generator is kept alive when a disconnect happens. It defaults to 30 seconds. This allows
you to reconnect the proxy and continue using the remote generator as if nothing happened
(see :py:meth:`Pyro5.client.Proxy._pyroReconnect` or even :ref:`reconnecting`). If you reconnect the
proxy and continue iterating again *after* the lingering timeout period expired, an exception is thrown
because the remote generator has been discarded in the meantime.
Lingering can be disabled completely by setting the value to 0, then all remote generators from a proxy will
immediately be discarded in the server if the proxy gets disconnected or closed.

There are several examples that use the remote iterator feature.
Have a look at the :py:mod:`streaming`, :py:mod:`stockquotes`, or the :py:mod:`filetransfer` examples.


.. index:: callback

Pyro Callbacks
==============
Usually there is a nice separation between a server and a client.
But with some Pyro programs it is not that simple.
It isn't weird for a Pyro object in a server somewhere to invoke a method call
on another Pyro object, that could even be running in the client program doing the initial call.
In this case the client program is a server itself as well.

These kinds of 'reverse' calls are labeled *callbacks*. You have to do a bit of
work to make them possible, because normally, a client program is not running the required
code to also act as a Pyro server to accept incoming callback calls.

In fact, you have to start a Pyro daemon and register the callback Pyro objects in it,
just as if you were writing a server program.
Keep in mind though that you probably have to run the daemon's request loop in its own
background thread. Or make heavy use of oneway method calls.
If you don't, your client program won't be able to process the callback requests because
it is by itself still waiting for results from the server.

.. index::
    single: exception in callback
    single: @Pyro5.api.callback
    double: decorator; callback

**Exceptions in callback objects:**
If your callback object raises an exception, Pyro will return that to the server doing the
callback. Depending on what the server does with it, you might never see the actual exception,
let alone the stack trace. This is why Pyro provides a decorator that you can use
on the methods in your callback object in the client program: ``@Pyro5.api.callback``.
This way, an exception in that method is not only returned to the caller, but also
logged locally in your client program, so you can see it happen including the
stack trace (if you have logging enabled)::

    import Pyro5.api

    class Callback(object):

        @Pyro5.api.expose
        @Pyro5.api.callback
        def call(self):
            print("callback received from server!")
            return 1//0    # crash!

Also notice that the callback method (or the whole class) has to be decorated
with ``@Pyro5.api.expose`` as well to allow it to be called remotely at all.
See the :py:mod:`callback` example for more details and code.


.. index:: misc features

Miscellaneous features
======================
Pyro provides a few miscellaneous features when dealing with remote method calls.
They are described in this section.

.. index:: error handling

Error handling
--------------
You can just do exception handling as you would do when writing normal Python code.
However, Pyro provides a few extra features when dealing with errors that occurred in
remote objects. This subject is explained in detail its own chapter: :doc:`errors`.

See the :py:mod:`exceptions` example for more details.

.. index:: timeouts

Timeouts
--------
Because calls on Pyro objects go over the network, you might encounter network related problems that you
don't have when using normal objects. One possible problems is some sort of network hiccup
that makes your call unresponsive because the data never arrived at the server or the response never
arrived back to the caller.

By default, Pyro waits an indefinite amount of time for the call to return. You can choose to
configure a *timeout* however. This can be done globally (for all Pyro network related operations)
by setting the timeout config item::

    Pyro5.config.COMMTIMEOUT = 1.5      # 1.5 seconds

You can also do this on a per-proxy basis by setting the timeout property on the proxy::

    proxy._pyroTimeout = 1.5    # 1.5 seconds


See the :py:mod:`timeout` example for more details.

Also, there is a automatic retry mechanism for timeout or connection closed (by server side),
in order to use this automatically retry::

    Pyro5.config.MAX_RETRIES = 3      # attempt to retry 3 times before raise the exception

You can also do this on a pre-proxy basis by setting the max retries property on the proxy::

    proxy._pyroMaxRetries = 3      # attempt to retry 3 times before raise the exception

Be careful to use when remote functions have a side effect (e.g.: calling twice results in error)!
See the :py:mod:`autoretry` example for more details.

.. index::
    double: reconnecting; automatic

.. _reconnecting:

Automatic reconnecting
----------------------
If your client program becomes disconnected to the server (because the server crashed for instance),
Pyro will raise a :py:exc:`Pyro5.errors.ConnectionClosedError`.
You can use the automatic retry mechanism to handle this exception, see the :py:mod:`autoretry` example for more details.
Alternatively, it is also possible to catch this and tell Pyro to attempt to reconnect to the server by calling
``_pyroReconnect()`` on the proxy (it takes an optional argument: the number of attempts
to reconnect to the daemon. By default this is almost infinite). Once successful, you can resume operations
on the proxy::

    try:
        proxy.method()
    except Pyro5.errors.ConnectionClosedError:
        # connection lost, try reconnecting
        obj._pyroReconnect()

This will only work if you take a few precautions in the server. Most importantly, if it crashed and comes
up again, it needs to publish its Pyro objects with the exact same URI as before (object id, hostname, daemon
port number).

See the :py:mod:`autoreconnect` example for more details and some suggestions on how to do this.

The ``_pyroReconnect()`` method can also be used to force a newly created proxy to connect immediately,
rather than on first use.


.. index:: proxy sharing

Proxy sharing between threads
-----------------------------

A proxy is 'owned' by a thread. You cannot use it from another thread.
Pyro does not allow you to share the same proxy across different threads,
because concurrent access to the same network connection will likely corrupt the
data sequence.

You can explicitly transfer ownership of a proxy to another thread via the proxy's ``_pyroClaimOwnership()`` method.
The current thread then claims the ownership of this proxy from another thread. Any existing connection will remain active.

See the :py:mod:`threadproxysharing` example for more details.


.. index::
    double: Daemon; Metadata

.. _metadata:

Metadata from the daemon
------------------------
A proxy contains some meta-data about the object it connects to.
It obtains the data via the (public) :py:meth:`Pyro5.server.DaemonObject.get_metadata` method on the daemon
that it connects to. This method returns the following information about the object (or rather, its class):
what methods and attributes are defined, and which of the methods are to be called as one-way.
This information is used to properly execute one-way calls, and to do client-side validation of calls on the proxy
(for instance to see if a method or attribute is actually available, without having to do a round-trip to the server).
Also this enables a properly working ``hasattr`` on the proxy, and efficient and specific error messages
if you try to access a method or attribute that is not defined or not exposed on the Pyro object.
Lastly the direct access to attributes on the remote object is also made possible, because the proxy knows about what
attributes are available.
