*****************
Intro and Example
*****************

.. image:: _static/pyro-large.png
  :align: center

This chapter contains a little overview of Pyro's features and a simple example to show how it looks like.


.. index:: features

Features
========

Pyro enables you to build applications in which
objects can talk to each other over the network, with minimal programming effort.
You can just use normal Python method calls, and Pyro takes care of locating the right object on the right
computer to execute the method. It is designed to be very easy to use, and to
stay out of your way. But it also provides a set of powerful features that
enables you to build distributed applications rapidly and effortlessly.
Pyro is a pure Python library and runs on many different platforms and Python versions.

Here's a quick overview of Pyro's features:

- written in 100% Python so extremely portable, runs on Python 3.x and also Pypy3
- works between different system architectures and operating systems.
- able to communicate between different Python versions transparently.
- defaults to a safe serializer (`serpent <https://pypi.python.org/pypi/serpent>`_) that supports many Python data types.
- supports different serializers (serpent, json, marshal, msgpack).
- can use IPv4, IPv6 and Unix domain sockets.
- optional secure connections via SSL/TLS (encryption, authentication and integrity), including certificate validation on both ends (2-way ssl).
- lightweight client library available for .NET and Java native code ('Pyrolite', provided separately).
- designed to be very easy to use and get out of your way as much as possible, but still provide a lot of flexibility when you do need it.
- name server that keeps track of your object's actual locations so you can move them around transparently.
- yellow-pages type lookups possible, based on metadata tags on registrations in the name server.
- support for automatic reconnection to servers in case of interruptions.
- automatic proxy-ing of Pyro objects which means you can return references to remote objects just as if it were normal objects.
- one-way invocations for enhanced performance.
- batched invocations for greatly enhanced performance of many calls on the same object.
- remote iterator on-demand item streaming avoids having to create large collections upfront and transfer them as a whole.
- you can define timeouts on network communications to prevent a call blocking forever if there's something wrong.
- remote exceptions will be raised in the caller, as if they were local. You can extract detailed remote traceback information.
- http gateway available for clients wanting to use http+json (such as browser scripts).
- stable network communication code that has worked reliably on many platforms for over a decade.
- can hook onto existing sockets created for instance with socketpair() to communicate efficiently between threads or sub-processes.
- possibility to integrate Pyro's event loop into your own (or third party) event loop.
- three different possible instance modes for your remote objects (singleton, one per session, one per call).
- many simple examples included to show various features and techniques.
- large amount of unit tests and high test coverage.
- reliable and established: built upon more than 20 years of existing Pyro history, with ongoing support and development.


.. index:: usage

What can you use Pyro for?
==========================

Essentially, Pyro can be used to distribute and integrate various kinds of resources or responsibilities:
computational (hardware) resources (cpu, storage, printers),
informational resources (data, privileged information)
and business logic (departments, domains).

An example would be a high performance compute cluster with a large storage system attached to it.
Usually this is not accessible directly, rather, smaller systems connect to it and
feed it with jobs that need to run on the big cluster. Later, they collect the results.
Pyro could be used to expose the available resources on the cluster to other computers.
Their client software connects to the cluster and calls the Python program there to perform its
heavy duty work, and collect the results (either directly from a method call return value,
or perhaps via asynchronous callbacks).

Remote controlling resources or other programs is a nice application as well.
For instance, you could write a simple
remote controller for your media server that is running on a machine somewhere in a closet.
A simple remote control client program could be used to instruct the media server
to play music, switch playlists, etc.

Another example is the use of Pyro to implement a form of `privilege separation <http://en.wikipedia.org/wiki/Privilege_separation>`_.
There is a small component running with higher privileges, but just able to execute the few tasks (and nothing else)
that require those higher privileges. That component could expose one or more Pyro objects
that represent the privileged information or logic.
Other programs running with normal privileges can talk to those Pyro objects to
perform those specific tasks with higher privileges in a controlled manner.

Finally, Pyro can be a communication glue library to easily integrate various pars of a heterogeneous system,
consisting of many different parts and pieces. As long as you have a working (and supported) Python version
running on it, you should be able to talk to it using Pyro from any other part of the system.

Have a look at the :file:`examples` directory in the source archive, perhaps one of the many example
programs in there gives even more inspiration of possibilities.


.. index:: upgrading from Pyro4

Upgrading from Pyro4
====================

Pyro5 is the current version. It is based on most of the concepts of Pyro4, but includes some major improvements.
Using it should be very familiar to current Pyro4 users, however Pyro5 is not compatible with Pyro4 and vice versa.
To allow graceful upgrading, both versions can co-exist due to the new package name
(the same happened years ago when Pyro 3 was upgraded to Pyro4).

Pyro5 provides a basic backward-compatibility module so much of existing Pyro4 code doesn't have to
change (apart from adding a single import statement).
This only works for code that imported Pyro4 symbols from the Pyro4 module
directly, instead of from one of Pyro4's sub modules. So, for instance:
``from Pyro4 import Proxy`` instead of: ``from Pyro4.core import Proxy``.
*some* submodules are more or less emulated such as ``Pyro4.errors``, ``Pyro4.socketutil``.
So you may first have to convert your old code to use the importing scheme to
only import the Pyro4 module and not from its submodules, and then you should
insert this at the top to enable the compatibility layer::

    from Pyro5.compatibility import Pyro4



What has been changed since Pyro4
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you're familiar with Pyro4, most of the things are the same in Pyro5. These are the changes though:

- Requires Python 3.7 or newer.
- the Pyro5 API is redesigned and this library is not compatible with Pyro4 code (although everything should be familiar):

      - Pyro5 is the new package name
      - restructured the submodules, renamed some submodules (naming -> nameserver,
        message -> protocol, util -> serializers)
      - most classes and method names are the same or at least similar but may have been shuffled around to other modules
      - all toplevel functions are renamed to pep8 code style (but class method names are unchanged from Pyro4 for now)
      - instead of the global package namespace you should now ``import Pyro5.api`` if you want to have one place to access the most important things
      - *compatibility layer:* to make upgrading easier there's a (limited) Pyro4 compatibility layer,
        enable this by ``from Pyro5.compatibility import Pyro4`` at the top of your modules. Read the docstring of this module for more details.

- Proxy moved from core to new client module
- Daemon moved from core to new server module
- no support for unsafe serializers AT ALL (pickle, dill, cloudpickle) - only safe serializers (serpent, marshal, json, msgpack)
- for now, requires ``msgpack`` to be installed as well as ``serpent``.
- no need anymore for the ability to configure the accepted serializers in a daemon, because of the previous change
- removed some other obscure config items
- removed all from future imports and all sys.version_info checks because we're Python 3 only
- removed Flame (utils/flameserver.py, utils/flame.py)  (although maybe the remote module access may come back in some form)
- moved test.echoserver to utils.echoserver (next to httpgateway)
- threadpool module moved into the same module as threadpool-server
- moved the multiplex and thread socketservers modules into main package
- no custom futures module anymore (you should use Python's own concurrent.futures instead)
- async proxy removed (may come back but probably not directly integrated into the Proxy class)
- batch calls now via client.BatchProxy, no convenience functions anymore ('batch')
- nameserver storage option 'dbm' removed (only memory and sql possible now)
- naming_storage module merged into nameserver module
- no Hmac key anymore, use SSL and 2-way certs if you want true security
- metadata in proxy can no longer be switched off
- having to use the @expose decorator to expose classes or methods can no longer be switched off
- @expose and other decorators moved from core to new server module
- now prefers ipv6 over ipv4 if your os agrees
- autoproxy always enabled for now (but this feature may be removed completely though)
- values from constants module scattered to various other more relevant modules
- util traceback and excepthook functions moved to errors module
- util methods regarding object/class inspection moved to new server module
- rest of util module renamed to serializers module
- replaced deprecated usages of optparse with argparse
- moved metadata search in the name server to a separate yplookup method (instead of using list as well)
- proxy doesn't have a thread lock anymore and no can longer be shared across different threads.
  A single thread is the sole "owner" of a proxy. Another thread can use proxy._pyroClaimOwnership to take over.
- simplified serializers by moving the task of compressing data to the protocol module instead (where it belonged)
- optimized wire messages (less code, sometimes less data copying by using memoryviews, no more checksumming)
- much larger annotations possible (4Gb instead of 64Kb) so it can be (ab)used for things like efficient binary data transfer
- annotations on the protocol message are now stored as no-copy memoryviews. A memoryview doesn't support all
  methods you might expect so sometimes it may be required now to convert it to bytes or bytearray in your
  own code first, before further processing. Note that this will create a copy again, so it's best avoided.


.. index:: example

Simple Example
==============

This example will show you in a nutshell what it's like to use Pyro in your programs.
A much more extensive introduction is found in the :doc:`tutorials`.
Here, we're making a simple greeting service that will return a personalized greeting message to its callers.
First let's see the server code::

    # saved as greeting-server.py
    import Pyro5.api

    @Pyro5.api.expose
    class GreetingMaker(object):
        def get_fortune(self, name):
            return "Hello, {0}. Here is your fortune message:\n" \
                   "Behold the warranty -- the bold print giveth and the fine print taketh away.".format(name)

    daemon = Pyro5.api.Daemon()             # make a Pyro daemon
    uri = daemon.register(GreetingMaker)    # register the greeting maker as a Pyro object

    print("Ready. Object uri =", uri)       # print the uri so we can use it in the client later
    daemon.requestLoop()                    # start the event loop of the server to wait for calls

Open a console window and start the greeting server::

    $ python greeting-server.py
    Ready. Object uri = PYRO:obj_fbfd1d6f83e44728b4bf89b9466965d5@localhost:35845

Great, our server is running. Let's see the client code that invokes the server::

    # saved as greeting-client.py
    import Pyro5.api

    uri = input("What is the Pyro uri of the greeting object? ").strip()
    name = input("What is your name? ").strip()

    greeting_maker = Pyro5.api.Proxy(uri)     # get a Pyro proxy to the greeting object
    print(greeting_maker.get_fortune(name))   # call method normally

Start this client program (from a different console window)::

    $ python greeting-client.py
    What is the Pyro uri of the greeting object?  <<paste the uri that the server printed earlier>>
    What is your name?  <<type your name; in my case: Irmen>>
    Hello, Irmen. Here is your fortune message:
    Behold the warranty -- the bold print giveth and the fine print taketh away.

As you can see the client code called the greeting maker that was running in the server elsewhere,
and printed the resulting greeting string.

With a name server
^^^^^^^^^^^^^^^^^^
While the example above works, it could become tiresome to work with object uris like that.
There's already a big issue, *how is the client supposed to get the uri, if we're not copy-pasting it?*
Thankfully Pyro provides a *name server* that works like an automatic phone book.
You can name your objects using logical names and use the name server to search for the
corresponding uri.

We'll have to modify a few lines in :file:`greeting-server.py` to make it register the object in the name server::

    # saved as greeting-server.py
    import Pyro5.api

    @Pyro5.api.expose
    class GreetingMaker(object):
        def get_fortune(self, name):
            return "Hello, {0}. Here is your fortune message:\n" \
                   "Tomorrow's lucky number is 12345678.".format(name)

    daemon = Pyro5.server.Daemon()         # make a Pyro daemon
    ns = Pyro5.api.locate_ns()             # find the name server
    uri = daemon.register(GreetingMaker)   # register the greeting maker as a Pyro object
    ns.register("example.greeting", uri)   # register the object with a name in the name server

    print("Ready.")
    daemon.requestLoop()                   # start the event loop of the server to wait for calls

The :file:`greeting-client.py` is actually simpler now because we can use the name server to find the object::

    # saved as greeting-client.py
    import Pyro5.api

    name = input("What is your name? ").strip()

    greeting_maker = Pyro5.api.Proxy("PYRONAME:example.greeting")    # use name server object lookup uri shortcut
    print(greeting_maker.get_fortune(name))

The program now needs a Pyro name server that is running. You can start one by typing the
following command: :command:`python -m Pyro5.nameserver` (or simply: :command:`pyro5-ns`) in a separate console window
(usually there is just *one* name server running in your network).
After that, start the server and client as before.
There's no need to copy-paste the object uri in the client any longer, it will 'discover'
the server automatically, based on the object name (:kbd:`example.greeting`).
If you want you can check that this name is indeed known in the name server, by typing
the command :command:`python -m Pyro5.nsc list` (or simply: :command:`pyro5-nsc list`), which will produce::

    $ pyro5-nsc list
    --------START LIST
    Pyro.NameServer --> PYRO:Pyro.NameServer@localhost:9090
        metadata: {'class:Pyro5.nameserver.NameServer'}
    example.greeting --> PYRO:obj_198af10aa51f4fa8ab54062e65fad96a@localhost:44687
    --------END LIST

(Once again the uri for our object will be random)
This concludes this simple Pyro example.

.. note::
 In the source archive there is a directory :file:`examples` that contains a truckload
 of example programs that show the various features of Pyro. If you're interested in them
 (it is highly recommended to be so!) you will have to download the Pyro distribution archive.
 Installing Pyro only provides the library modules. For more information, see :doc:`config`.

Other means of creating connections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The example above showed two of the basic ways to set up connections between your client and server code.
There are various other options, have a look at the client code details: :ref:`object-discovery`
and the server code details: :ref:`publish-objects`. The use of the name server is optional, see
:ref:`name-server` for details.


.. index:: performance, benchmark

Performance
===========
Pyro is pretty fast, but speed depends largely on many external factors:

- network connection speed
- machine and operating system
- I/O or CPU bound workload
- contents and size of the pyro call request and response messages
- the serializer being used

Experiment with the ``benchmark``, ``batchedcalls`` and ``hugetransfer`` examples to see what results you get on your own setup.
