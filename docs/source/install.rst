.. index:: installing Pyro

***************
Installing Pyro
***************

This chapter will show how to obtain and install Pyro.

.. index::
    double: installing Pyro; requirements for Pyro

Compatibility
-------------
Pyro is written in 100% Python. It works on any recent operating system where a suitable supported Python implementation is available
(3.5 or newer).


.. index::
    double: installing Pyro; obtaining Pyro

Obtaining and installing Pyro
-----------------------------

**Linux**
    Some Linux distributions may offer Pyro5 through their package manager. Make sure you install the correct
    one for the python version that you are using. It may be more convenient to just pip install it instead
    in a virtualenv.

**Anaconda**
    There is not yet an Anaconda package for Pyro5. Use one of the other methods.

**Pip install**
    ``pip install Pyro5`` should do the trick.   Pyro is available `here <http://pypi.python.org/pypi/Pyro5/>`_  on pypi.

**Manual installation from source**
    Download the source distribution archive (Pyro5-X.YZ.tar.gz) from Pypi or Github, extract and ``python setup.py install``.
    The `serpent <https://pypi.python.org/pypi/serpent>`_ serialization library must also be installed.

**Github**
    Source is on Github: https://github.com/irmen/Pyro5
    The required serpent serializer library is there as well: https://github.com/irmen/Serpent


Third party libraries that Pyro5 uses
-------------------------------------

`serpent <https://pypi.python.org/pypi/serpent>`_ - required, 1.27 or newer
    Should be installed automatically when you install Pyro.

`msgpack <https://pypi.python.org/pypi/msgpack>`_ - optional, 0.5.2 or newer
    Install this to use the msgpack serializer.


Stuff you get extra in the source distribution archive and not with packaged versions
-------------------------------------------------------------------------------------
If you decide to download the distribution (.tar.gz) you have a bunch of extras over simply installing the Pyro library directly.
It contains:

  docs/
    the Sphinx/RST sources for this manual, https://pyro5.readthedocs.io/
  examples/
    dozens of examples that demonstrate various Pyro features (highly recommended to examine these,
    many paragraphs in this manual refer to relevant examples here)
  tests/
    the unittest suite that checks for correctness and regressions
  Pyro5/
    The actual Pyro library's source code (only this part is installed if you install the ``Pyro5`` package)
  and a couple of other files:
    a setup script and other miscellaneous files such as the license (see :doc:`license`).
