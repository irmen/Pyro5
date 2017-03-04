Pyro5
=====

*Remote objects communication library for Python 3, fifth incarnation*

This may or may not become the next major Pyro version.
It will only work on Python 3.5 or later (or perhaps 3.4 or later).

It is based on Pyro4 and the basic concepts are all the same, but there are a few major differences:

- no python 2.x compatibility anymore. This also means goodbye to Jython and Ironpython (until they release python 3.x versions of their implementation)
- the API is similar but not compatible to existing code:
-- Pyro5 is the new package name
-- restructuring of the sub modules, other module names
-- many classes and method names are the same or at least similar, but may have been shuffled around to other modules
-- instead of the global package namespace (Pyro4) you should now use Pyro5.api where the most important things are aggregated together


This package is still largely untested and in development.

You should use Pyro4 instead for now: https://github.com/irmen/Pyro4
