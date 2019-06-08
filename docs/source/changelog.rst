**********
Change Log
**********

**Pyro 5.4**

- begun making Pyro5 specific documentation instead of referring to Pyro4
- tox tests now include Python 3.8 as well (because 3.8 beta was released recently)


**Pyro 5.3**

various things ported over from recent Pyro4 changes:

- added a few more methods to the 'private' list
- fix thread server worker thread name
- on windows, the threaded server can now also be stopped with ctrl-c (sigint)
- NATPORT behavior fix when 0
- source dist archive is more complete now
- small fix for cython


**Pyro 5.2**

- travis CI python3.7 improvements
- serialization improvements/fixes
- reintroduced config object to make a possibility for a non-static (non-global) pyro configuration


**Pyro 5.1**

- python 3.5 or newer is now required
- socketutil module tweaks and cleanups
- added a bunch of tests, taken from pyro4 mostly, for the socketutil module
- moved to declarative setup.cfg rather than in setup.py
- made sure the license is included in the distribution


**Pyro 5.0**

- first public release
