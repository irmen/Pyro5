**********
Change Log
**********

**Pyro 5.13.1**

- fixed @expose issue on static method/classmethod due to API change in Python 3.10


**Pyro 5.13**

- removed Python 3.6 from the support list (it is EOL). Now supported on Python 3.7 or newer
- corrected documentation about autoproxy: this feature is not configurable, it is always active.
- introduced SERPENT_BYTES_REPR config item (and updated serpent library version requirement for this)
- flush nameserver output to console before entering request loop
- added optional boolean "weak" parameter to Daemon.register(), to register a weak reference to the server object
  that will be unregistered automatically when the server object gets deleted.
- switched from travis to using github actions for CI builds and tests


**Pyro 5.12**

- fixed error when import Pyro5.server   (workaround was to import Pyro5.core before it)
- documented SSL_CACERTS config item
- removed Python 3.5 from the support list (it is EOL). Now requires Python 3.6 or newer


**Pyro 5.11**

- reworked the timezones example. (it didn't work as intended)
- httpgateway message data bytearray type fix
- fixed ipv6 error in filetransfer example
- added methodcall_error_handler in documentation


**Pyro 5.10**

- finally ported over the unit test suite from Pyro4
- finally updated the documentation from Pyro4 to Pyro5 (there's likely still some errors or omissions though)
- fixed regex lookup index error in nameserver
- the 4 custom class (un)register methods on the SerializerBase class are now also directly available in the api module



**Pyro 5.9.2**

- fixed a silent error in the server when doing error handling (avoid calling getpeername() which may fail)
  this issue could cause a method call to not being executed in a certain specific scenario.
  (oneway call on MacOS when using unix domain sockets). Still, it's probably wise to upgrade as
  this was a regression since version 5.8.


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
