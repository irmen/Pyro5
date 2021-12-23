Pyro5
=====

*Remote objects communication library*

.. image:: https://img.shields.io/pypi/v/Pyro5.svg
    :target: https://pypi.python.org/pypi/Pyro5

.. image:: https://anaconda.org/conda-forge/pyro5/badges/version.svg
    :target: https://anaconda.org/conda-forge/pyro5

.. image:: https://img.shields.io/lgtm/grade/python/g/irmen/Pyro5.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/irmen/Pyro5/context:python

.. image:: https://img.shields.io/lgtm/alerts/g/irmen/Pyro5.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/irmen/Pyro5/alerts


Info
----

Pyro enables you to build applications in which
objects can talk to each other over the network, with minimal programming effort.
You can just use normal Python method calls, and Pyro takes care of locating the right object on the right
computer to execute the method. It is designed to be very easy to use, and to
stay out of your way. But it also provides a set of powerful features that
enables you to build distributed applications rapidly and effortlessly.
Pyro is a pure Python library and runs on many different platforms and Python versions.


Pyro is copyright © Irmen de Jong (irmen@razorvine.net | http://www.razorvine.net).  Please read the file ``license``.

Pyro can be found on Pypi as `Pyro5 <http://pypi.python.org/pypi/Pyro5/>`_.  Source is on Github: https://github.com/irmen/Pyro5
Documentation is here: https://pyro5.readthedocs.io/

Pyro5 is the current version of Pyro. `Pyro4 <https://pyro4.readthedocs.io/>`_ is the predecessor
that only gets important bugfixes and security fixes, but is otherwise no longer being improved.
New code should use Pyro5 if at all possible.


Features
--------

- written in 100% Python so extremely portable, supported on Python 3.7 and newer, and Pypy3
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

