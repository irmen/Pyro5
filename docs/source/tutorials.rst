.. include:: <isonum.txt>
.. index:: tutorial

********
Tutorial
********

This tutorial will explain a couple of basic Pyro concepts.

Warm-up
=======

Before proceeding, you should install Pyro if you haven't done so. For instructions about that, see :doc:`install`.

In this tutorial, you will use Pyro's default configuration settings, so once Pyro is installed, you're all set!
All you need is a text editor and a couple of console windows.
During the tutorial, you are supposed to run everything on a single machine.
This avoids initial networking complexity.

.. note::
    For security reasons, Pyro runs stuff on localhost by default.
    If you want to access things from different machines, you'll have to tell Pyro
    to do that explicitly.

.. index::
    double: tutorial; concepts and tools

Pyro concepts and tools
=======================

Pyro enables code to call methods on objects even if that object is running on a remote machine::

    +----------+                         +----------+
    | server A |                         | server B |
    |          |       < network >       |          |
    | Python   |                         |   Python |
    | OBJECT ----------foo.invoke()--------> OBJECT |
    |          |                         |     foo  |
    +----------+                         +----------+

Pyro is mainly used as a library in your code but it also has several supporting command line tools.
We won't explain every one of them here as you will only need the "name server" for this tutorial.

.. _keyconcepts:

Key concepts
^^^^^^^^^^^^
Here are a couple of key concepts you encounter when using Pyro:

Proxy
    A proxy is a substitute object for "the real thing".
    It intercepts the method calls you would normally do on an object as if it was the actual object.
    Pyro then performs some magic to transfer the call to the computer that contains the *real* object,
    where the actual method call is done, and the results are returned to the caller.
    This means the calling code doesn't have to know if it's dealing with a normal or a remote object,
    because the code is identical.
    The class implementing Pyro proxies is ``Pyro5.client.Proxy``

:abbr:`URI (Unique resource identifier)`
    This is what Pyro uses to identify every object.
    (similar to what a web page URL is to point to the different documents on the web).
    Its string form is like this: "PYRO:" + object name + "@" + server name + port number.
    There are a few other forms it can take as well.
    You can write the protocol in lowercase too if you want ("pyro:") but it will
    automatically be converted to uppercase internally.
    The class implementing Pyro uris is ``Pyro5.core.URI``

Pyro object
    This is a normal Python object but it is registered with Pyro so that you can access it remotely.
    Pyro objects are written just as any other object but the fact that Pyro knows something about
    them makes them special, in the way that you can call methods on them from other programs.
    A class can also be a Pyro object, but then you will also have to tell Pyro about how it
    should create actual objects from that class when handling remote calls.

Pyro daemon (server)
    This is the part of Pyro that listens for remote method calls, dispatches them
    to the appropriate actual objects, and returns the results to the caller.
    All Pyro objects are registered in one or more daemons.

Pyro name server
    The name server is a utility that provides a phone book for Pyro applications: you use it to look up a "number" by a "name".
    The name in Pyro's case is the logical name of a remote object. The number is the exact location where Pyro can contact the object.

Serialization
    This is the process of transforming objects into streams of bytes that can be transported
    over the network. The receiver deserializes them back into actual objects. Pyro needs to do
    this with all the data that is passed as arguments to remote method calls, and their response
    data. Not all objects can be serialized, so it is possible that passing a certain object to
    Pyro won't work even though a normal method call would accept it just fine.

Configuration
    Pyro can be configured in a lot of ways. Using environment variables (they're prefixed with ``PYRO_``)
    or by setting config items in your code. See the configuration chapter for more details.
    The default configuration should be ok for most situations though, so you many never have to touch
    any of these options at all!


Starting a name server
^^^^^^^^^^^^^^^^^^^^^^

While the use of the Pyro name server is optional, we will use it in this tutorial.
It also shows a few basic Pyro concepts, so let us begin by explaining a little about it.
Open a console window and execute the following command to start a name server:

:command:`python -m Pyro5.nameserver` (or simply: :command:`pyro5-ns`)

The name server will start and it prints something like::

    Not starting broadcast server for IPv6.
    NS running on localhost:9090 (::1)
    URI = PYRO:Pyro.NameServer@localhost:9090


.. sidebar:: Localhost

   By default, Pyro uses *localhost* to run stuff on, so you can't by mistake expose your system to the outside world.
   You'll need to tell Pyro explicitly to use something else than *localhost*. But it is fine for the tutorial,
   so we leave it as it is.

The name server has started and is listening on *localhost port 9090*. (If your operating system supports it,
it will likely use Ipv6 as well rather than the older Ipv4 addressing).

It also printed an :abbr:`URI (unique resource identifier)`. Remember, this is
what Pyro uses to identify every object. The nameserver itself is also just a Pyro object!

The name server can be stopped with a :kbd:`control-c`, or on Windows, with :kbd:`ctrl-break`. But let it run
in the background for the rest of this tutorial.


Interacting with the name server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There's another command line tool that let you interact with the name server: "nsc" (name server control tool).
You can use it, amongst other things, to see what all known registered objects in the naming server are.
Let's do that right now. Type:

:command:`python -m Pyro5.nsc list` (or simply: :command:`pyro5-nsc list`)

and it will print something like this::

    --------START LIST
    Pyro.NameServer --> PYRO:Pyro.NameServer@localhost:9090
        metadata: {'class:Pyro5.nameserver.NameServer'}
    --------END LIST

The only object that is currently registered, is the name server itself! (Yes, the name server is a Pyro object
itself. Pyro and the "nsc" tool are using Pyro to talk to it).

.. note:: As you can see, the name ``Pyro.NameServer`` is registered to point to the URI that we saw earlier.
   This is mainly for completeness sake, and is not often used, because there are different ways to get
   to talk to the name server (see below).

.. sidebar:: The NameServer object

  The name server itself is a normal Pyro object which means the 'nsc' tool, and any other code that talks to it,
  is just using normal Pyro methods. What makes it a bit different from other Pyro servers
  is that is includes a broadcast responder (for discovery).


There's a little detail left unexplained: *How did the nsc tool know where the name server was?*

Pyro has a couple of ways to locate a name server.  The nsc tool uses those too:
there is a network broadcast discovery to see if there's a name server available somewhere (the name server contains
a broadcast responder that will respond "Yeah hi I'm here").  So in many cases you won't have to configure anything
to be able to discover the name server. If nobody answers though, Pyro tries the configured default or custom location.
If still nobody answers it prints a sad message and exits.
However if it found the name server, it is then possible to talk to it and get the location of any other registered object.
This means that you won't have to hard code any object locations in your code,
and that the code is capable of dynamically discovering everything at runtime.


Not using the Name server
=========================
In both tutorials above we used the Name Server for easy object lookup.
The use of the name server is optional, see :ref:`name-server` for details.
There are various other options for connecting your client code to your Pyro objects,
have a look at the client code details: :ref:`object-discovery`
and the server code details: :ref:`publish-objects`.



.. index:: tutorial

Tutorial examples
=================

Pyro5 includes dozens of examples. You can find them in the `source distribution <https://github.com/irmen/Pyro5/archive/master.zip>`_,
or `online on github <https://github.com/irmen/Pyro5/tree/master/examples>`_.

Historically, two of them (warehouse and stockmarket) were used in this manual to walk you through creating
a complete Pyro program.  You can still read these tutorials in the Pyro4 manual, they're still almost unchanged
in Pyro5 (follow along with the pyro5 example code to spot the few differences):

* Pyro4 tutorial `building a warehouse <https://pyro4.readthedocs.io/en/stable/tutorials.html#building-a-warehouse>`_
* Pyro4 tutorial `stockmarket simulator <https://pyro4.readthedocs.io/en/stable/tutorials.html#building-a-stock-market-simulator>`_

They're useful starting points (especially since the examples are created in multiple phases),
but there are many more concepts to explore in the other examples so don't hesitate to browse through them.
