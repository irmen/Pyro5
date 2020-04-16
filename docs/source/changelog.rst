**********
Change Log
**********

**Pyro 5.9.1**

- fixed some circular import conflicts
- fixed empty nameserver host lookup issue


**Pyro 5.9**

- added privilege-separation example
- added methodcall_error_handler to Daemon that allows you to provide a custom error handler,
  which is called when an exception occurs in the method call's user code
- introduced ``api.serve`` / ``server.serve`` as a replacement for the static class method ``Daemon.serveSimple``
- fix possible race condition when creating instances with instancemode "single"
- introduced some more type hintings


**Pyro 5.8**

- cython compatibility fix
- removed explicit version checks of dependencies such as serpent.
  This fixes crash error when dealing with prerelease versions that didn't match the pattern.


**Pyro 5.7**

- fixed possible attribute error in proxy del method at interpreter shutdown
- gave the serialization example a clearer name 'custom-serialization'
- added NS_LOOKUP_DELAY config item and parameter to resolve()
  to have an optional wait delay until a name becomes available in the nameserver
- added lookup() and yplookup() utility functions that implement this retry mechanism


**Pyro 5.6**

- improved and cleaned up exception handling throughout the code base
- URIs now accept spaces in the location part. This is useful for unix domain sockets.


**Pyro 5.5**

- made msgpack serializer optional
- Anaconda 'pyro5' package created


**Pyro 5.4**

- made the decision that Pyro5 will require Python 3.5 or newer, and won't support Python 2.7 (which will be EOL in january 2020)
- begun making Pyro5 specific documentation instead of referring to Pyro4
- tox tests now include Python 3.8 as well (because 3.8 beta was released recently)
- dropped support for Python 3.4 (which has reached end-of-life status). Supported Python versions are now 2.7, and 3.5 or newer.
  (the life cycle status of the Python versions can be seen here https://devguide.python.org/#status-of-python-branches)
- code cleanups, removing some old compatibility stuff etc.


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
