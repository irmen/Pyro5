Pyro5
=====

*Remote objects communication library, fifth major version*

.. image:: https://img.shields.io/badge/say-thanks-ff69b4.svg
    :target: https://saythanks.io/to/irmen

.. image:: https://travis-ci.org/irmen/Pyro5.svg?branch=master
    :target: https://travis-ci.org/irmen/Pyro5

.. image:: https://img.shields.io/pypi/v/Pyro5.svg
    :target: https://pypi.python.org/pypi/Pyro5

.. image:: https://anaconda.org/conda-forge/pyro5/badges/version.svg
    :target: https://anaconda.org/conda-forge/pyro5

.. image:: https://img.shields.io/lgtm/grade/python/g/irmen/Pyro5.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/irmen/Pyro5/context:python

.. image:: https://img.shields.io/lgtm/alerts/g/irmen/Pyro5.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/irmen/Pyro5/alerts


Pyro enables you to build applications in which objects can talk to each other over the network, with minimal programming effort. You can just use normal Python method calls to call objects on other machines. Pyro is a pure Python library so it runs on many different platforms and Python versions.

Pyro5 is the next major version of the Pyro library and requires Python 3.5 or later.


Documentation
-------------
Docs are here: https://pyro5.readthedocs.io/  (they are still being updated from Pyro4 to Pyro5)

What has changed since Pyro4
----------------------------

If you're familiar with Pyro4, most of the things are the same in Pyro5. These are the changes though:

- Requires Python 3.5 or newer.
- the Pyro5 API is redesigned and this library is not compatible with Pyro4 code (although everything should be familiar):

  - Pyro5 is the new package name (duh)
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


@TODO:

- separate protocol and network i/o logic to allow for async server implementation.
