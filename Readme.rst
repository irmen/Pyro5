Pyro5 - work in progress - use Pyro4 for now
============================================

*Remote objects communication library for Python 3, fifth incarnation*

**Don't use this yet, it is very much in development and can change or be canceled at any time. Use Pyro4 instead!**


This may or may not become the next major Pyro version.
It will only work on Python 3.4 or later. Python 2.x is no longer supported!
If you require compatibility with older Python versions, use Pyro4 instead.

Pyro5 is an "overhauled and updated" Pyro4: more efficient, simpler, streamlined, and cleaned up.



changes done based on original Pyro4 sources (release 4.62)
-----------------------------------------------------------

- the API is similar but incompatible:

  - Pyro5 is the new package name (duh)
  - restructured the submodules, renamed some submodules (naming -> nameserver, configuration -> config,
    message -> protocol, util -> serializers)
  - many classes and method names are the same or at least similar, but may have been shuffled around to other modules
  - all toplevel functions are renamed to pep8 code style, but class method names are unchanged from Pyro4
  - instead of the global package namespace you should now ``import Pyro5.api`` if you want to have one place to access the most important things

- Proxy moved from core to new client module
- Daemon moved from core to new server module
- no support for unsafe serializers AT ALL (pickle, dill, cloudpickle) - only safe serializers (serpent, marshal, json, msgpack)
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
- wire protocol changed: much larger annotations possible (4Gb instead of 64Kb), no more checksumming
- proxy doesn't have a thread lock anymore and no can longer be shared across different threads.
  A single thread is the sole "owner" of a proxy. Another thread can use proxy._pyroClaimOwnership to take over.
- simplified serializers by moving the task of compressing data to the protocol module instead (where it belonged)
- optimized wire messages (less code, sometimes less data copying by using memoryviews)
- for now, requires msgpack-python to be installed as well as serpent.


This library is still largely untested and in development.

You should use Pyro4 instead for now: https://github.com/irmen/Pyro4

