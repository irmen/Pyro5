.. index:: security

.. _security:

********
Security
********

.. warning::
    Do not publish any Pyro objects to remote machines unless you've read and understood everything
    that is discussed in this chapter. This is also true when publishing Pyro objects with different
    credentials to other processes on the same machine.
    Why? In short: using Pyro has several security risks. Pyro has a few countermeasures to deal with them.
    Understanding the risks, the countermeasures, and their limits, is very important to avoid
    creating systems that are very easy to compromise by malicious entities.

.. index::
    double: security; network interfaces

Network interface binding
=========================
By default Pyro binds every server on localhost, to avoid exposing things on a public network or over the internet by mistake.
If you want to expose your Pyro objects to anything other than localhost, you have to explicitly tell Pyro the
network interface address it should use. This means it is a conscious effort to expose Pyro objects to other machines.

It is possible to tell Pyro the interface address via an environment variable or global config item (``HOST``).
In some situations - or if you're paranoid - it is advisable to override this setting in your server program
by setting the config item from within your own code, instead of depending on an externally configured setting.


.. index::
    double: security; different user id

Running Pyro servers with different credentials/user id
=======================================================
The following is not a Pyro specific problem, but is important nonetheless:
If you want to run your Pyro server as a different user id or with different credentials as regular users,
*be very careful* what kind of Pyro objects you expose like this!

Treat this situation as if you're exposing your server on the internet (even when it's only running on localhost).
Keep in mind that it is still possible that a random user on the same machine connects to the local server.
You may need additional security measures to prevent random users from calling your Pyro objects.

.. index:: SSL, TLS
    double: security; encryption

Secure communication via SSL/TLS
================================
Pyro itself doesn't encrypt the data it sends over the network. This means if you use the default
configuration, you must never transfer sensitive data on untrusted networks
(especially user data, passwords, and such) because eavesdropping is possible.

You can run Pyro over a secure network (VPN, ssl/ssh tunnel) where the encryption
is taken care of externally. It is also possible however to enable SSL/TLS in Pyro itself,
so that all communication is secured via this industry standard that
provides encryption, authentication, and anti-tampering (message integrity).

**Using SSL/TLS**

Enable it by setting the ``SSL`` config item to True, and configure the other SSL config items
as required. You'll need to specify the cert files to use, private keys, and passwords if any.
By default, the SSL mode only has a cert on the server (which is similar to visiting a https url
in your browser). This means your *clients* can be sure that they are connecting to the expected
server, but the *server* has no way to know what clients are connecting.
You can solve this using SSL and custom certificate verification.
You can do this in your client (checks the server's cert) but you can also tell your clients
to use certs as well and check these in your server. This makes it 2-way-SSL or mutual authentication.
For more details see here :ref:`cert_verification`. The SSL config items are in :ref:`config-items`.

For example code on how to set up a 2-way-SSL Pyro client and server, with cert verification,
see the ``ssl`` example.

.. index::
    double: security; object traversal
    double: security; dotted names

Dotted names (object traversal)
===============================
Using "dotted names" to traverse attributes on Pyro proxies (like ``proxy.aaa.bbb.ccc()``)
is not possible. because that is a security vulnerability
(for similar reasons as described here https://legacy.python.org/news/security/PSF-2005-001/ ).

If you require access to a nested attribute, you'll have to explicitly add a method or attribute
on the proxy itself to access it directly.


.. index::
    double: security; environment variables

Environment variables overriding config items
=============================================
Almost all config items can be overwritten by an environment variable.
If you can't trust the environment in which your script is running, it may be a good idea
to reset the config items to their default builtin values, without using any environment variables.
See :doc:`config` for the proper way to do this.


Preventing arbitrary connections
================================

.. index:: certificate verification, 2-way-SSL

.. _cert_verification:

...by using 2-way-SSL and certificate verificiation
---------------------------------------------------

When using SSL, you should also do some custom certificate verification, such as checking the serial number
and commonName. This way your code is not only certain that the communication is encrypted, but also
that it is talking to the intended party and nobody else (middleman).
The server hostname and cert expiration dates *are* checked automatically, but
other attributes you have to verify yourself.

This is fairly easy to do: you can use :ref:`conn_handshake` for this. You can then get the peer certificate
using :py:meth:`Pyro5.socketutil.SocketConnection.getpeercert`.

If you configure a client cert as well as a server cert, you can/should also do verification of
client certificates in your server. This is a good way to be absolutely certain that you only
allow clients that you know and trust, because you can check the required unique certificate attributes.

Having certs on both client and server is called 2-way-SSL or mutual authentication.

It's a bit too involved to fully describe here but it not much harder than the basic SSL configuration
described earlier. You just have to make sure you supply a client certificate and that the server requires
a client certificate (and verifies some properties of it).
The ``ssl`` example shows how to do all this.
