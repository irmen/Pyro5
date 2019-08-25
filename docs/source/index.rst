****************************************
Pyro - Python Remote Objects - |version|
****************************************

.. image:: _static/pyro-large.png
    :align: center
    :alt: PYRO logo


**@TODO: THIS MANUAL IS STILL BEING UPDATED FROM Pyro4 TO Pyro5**


.. index:: what is Pyro

What is Pyro?
-------------
It is a library that enables you to build applications in which
objects can talk to each other over the network, with minimal programming effort.
You can just use normal Python method calls to call objects on other machines.
Pyro is a pure Python library and runs on many different platforms and Python versions.

Pyro is copyright © Irmen de Jong (irmen@razorvine.net | http://www.razorvine.net).  Please read :doc:`license`.

Pyro can be found on Pypi as `Pyro5 <http://pypi.python.org/pypi/Pyro5/>`_.  Source on Github: https://github.com/irmen/Pyro5

Pyro5 is the new major version of Pyro, and this is where new features and changes will appear.
Even though the API is pretty mature and extensible, there is no guarantee that no breaking API changes
will occur in new versions to support possible new features or improvements.

If you absolutely require a stable API, consider using `Pyro4 <http://pypi.python.org/pypi/Pyro4/>`_ for production code for now.
Pyro4 is in maintenance mode and only gets important bug fixes and security fixes, and no new features or other changes.


.. toctree::
   :maxdepth: 2
   :caption: Contents of this manual:

   intro.rst
   install.rst
   tutorials.rst
   commandline.rst
   clientcode.rst
   servercode.rst
   nameserver.rst
   security.rst
   errors.rst
   tipstricks.rst
   config.rst
   api.rst
   pyrolite.rst
   changelog.rst
   license.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

.. figure:: _static/tf_pyrotaunt.png
   :target: http://wiki.teamfortress.com/wiki/Pyro
   :alt: PYYYRRRROOOO
   :align:  center
