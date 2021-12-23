.. index:: installing Pyro

***************
Installing Pyro
***************

This chapter will show how to obtain and install Pyro.

.. index::
    double: installing Pyro; requirements for Pyro

Compatibility
-------------
Pyro is written in 100% Python. It works on any recent operating system where a suitable
supported Python implementation is available (3.7 or newer).


.. index::
    double: installing Pyro; obtaining Pyro

Obtaining and installing Pyro
-----------------------------

**Linux**
    Some Linux distributions may offer Pyro5 through their package manager. Make sure you install the correct
    one for the python version that you are using. It may be more convenient to just pip install it instead
    in a virtualenv.

**Anaconda**
    Anaconda users can install the Pyro5 package from conda-forge using ``conda install -c conda-forge pyro5``

**Pip install**
    ``pip install Pyro5`` should do the trick.   Pyro is available `here on pypi <http://pypi.python.org/pypi/Pyro5/>`_ .

**Manual installation from source**
    Download the source distribution archive (Pyro5-X.YZ.tar.gz) from Pypi or from a `Github release <https://github.com/irmen/Pyro5/releases>`_,
    extract it and ``python setup.py install``.
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


Interesting stuff that is extra in the source distribution archive and not with packaged versions
-------------------------------------------------------------------------------------------------
If you decide to download the distribution (.tar.gz) you have a bunch of extras over simply installing the Pyro library directly:

  examples/
    dozens of examples that demonstrate various Pyro features (highly recommended to examine these,
    many paragraphs in this manual refer to relevant examples here)

  tests/
    the unittest suite that checks for correctness and regressions
