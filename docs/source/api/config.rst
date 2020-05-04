:mod:`Pyro5.config` --- Configuration items
===========================================

Pyro's configuration is available in the ``Pyro5.config`` object.
Detailed information about the API of this object is available in the :doc:`/config` chapter.

.. note:: creation of the ``Pyro5.config`` object

  This object is constructed when you import Pyro5.
  It is an instance of the :class:`Pyro5.configure.Configuration` class.
  The package initializer code creates it and the initial configuration is
  determined (from defaults and environment variable settings).
  It is then assigned to ``Pyro5.config``.

