Pyro5
=====

*Remote objects communication library for Python 3, fifth incarnation*

**Don't use this yet, it is very much in development and can change or be canceled at any time. Use Pyro4 instead!**


This may or may not become the next major Pyro version.
It will only work on Python 3.5 or later (or perhaps 3.4 or later).
Python 2.x is no longer supported!

Pyro5 is an "overhauled" Pyro4: more secure, more efficent, simpler, streamlined and cleaned up.

It is based on the proven concepts of Pyro4 and a lot should be familiar, but there are some major differences:

- the API is similar but not compatible:
- - Pyro5 is the new package name (duh)
- - restructuring of the submodules, other module names
- - many classes and method names are the same or at least similar, but may have been shuffled around to other modules
- - instead of the global package namespace you should now use Pyro5.api if you want to have one place to access the most important things
- no async proxy (may come back but probably not directly integrated into the Proxy class)
- no custom futures module anymore (you should use Python's own concurrent.futures instead)
- no Hmac key anymore, will probably be replaced by a different security mechanism
- wire protocol changed (much larger annotations possible, no more checksumming)
- no support for unsafe serializers AT ALL (pickle, dill)
- no 'flame' utility anymore (although maybe the remote module access may come back in some form)
- using the @expose decorator to expose classes or methods is now required
- now prefers ipv6 over ipv4 if your os supports it
- autoproxy always enabled (but this feature may be removed completely though)
- a couple of other config items have been removed to make stuff easier.
- moved metadata search in the name server to a separate yplookup method.
- a proxy doesn't have a thread lock anymore but can't be shared anymore across different threads.
  A thread is the "owner" of a proxy. Another thread can use _pyroClaimOwnership to take over.


This package is still largely untested and in development.

You should use Pyro4 instead for now: https://github.com/irmen/Pyro4



