Pyro5 [work in progress]
========================

*Remote objects communication library, fifth major version*

.. image:: https://img.shields.io/badge/say-thanks-ff69b4.svg
    :target: https://saythanks.io/to/irmen

.. image:: https://travis-ci.org/irmen/Pyro5.svg?branch=master
    :target: https://travis-ci.org/irmen/Pyro5


Pyro5 is an "overhauled, updated and modernized" Pyro4 (https://github.com/irmen/Pyro4):
more efficient, faster, simpler, streamlined, and cleaned up. It requires Python 3.4 or later!

I'm aiming to separate the actual network logic and the protocol/messaging logic so that it will be possible
to use the protocol logic in different network i/o setups (such as an async eventloop based solution).

This may or may not become the actual next major Pyro version. Feel free to report issues for suggestions or problems!

**This is very much in development and can change or be canceled at any time. Use Pyro4 https://github.com/irmen/Pyro4 for real work instead.**


changes done based on original Pyro4
------------------------------------

- the Pyro5 API is redesigned and this library is not compatible with Pyro4 code (although everything should be familiar):

  - Pyro5 is the new package name (duh)
  - restructured the submodules, renamed some submodules (naming -> nameserver, configuration -> config,
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

- create an alternative for Pyro4's async proxy, and fix the examples that use it: distributed-computing2, distributed-mandelbrot
- separate protocol and network i/o logic to allow for async server implementation.
