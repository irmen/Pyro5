.. index:: configuration

****************
Configuring Pyro
****************

Pyro can be configured using several *configuration items*.
The current configuration is accessible from the ``Pyro5.config`` object, it contains all config items as attributes.
You can read them and update them to change Pyro's configuration.
(usually you need to do this at the start of your program).
For instance, to enable message compression and change the server type, you add something like this to the start of your code::

  Pyro5.config.COMPRESSION = True
  Pyro5.config.SERVERTYPE = "multiplex"

.. index::
    double: configuration; environment variables

You can also set them outside of your program, using environment variables from the shell.
**To avoid conflicts, the environment variables have a ``PYRO_`` prefix.** This means that if you want
to change the same two settings as above, but by using environment variables, you would do something like::

    $ export PYRO_COMPRESSION=true
    $ export PYRO_SERVERTYPE=multiplex

    (or on windows:)
    C:\> set PYRO_COMPRESSION=true
    C:\> set PYRO_SERVERTYPE=multiplex

This environment defined configuration is simply used as initial values for Pyro's configuration object.
Your code can still overwrite them by setting the items to other values, or by resetting the config as a whole.


.. index:: reset config to default

Resetting the config to default values
--------------------------------------

.. method:: Pyro5.config.reset([use_environment=True])

    Resets the configuration items to their builtin default values.
    If `use_environment` is True, it will overwrite builtin config items with any values set
    by environment variables. If you don't trust your environment, it may be a good idea
    to reset the config items to just the builtin defaults (ignoring any environment variables)
    by calling this method with `use_environment` set to False.
    Do this before using any other part of the Pyro library.


.. index:: current config, pyro5-check-config

Inspecting current config
-------------------------

To inspect the current configuration you have several options:

1. Access individual config items: ``print(Pyro5.config.COMPRESSION)``
2. Dump the config in a console window: :command:`python -m Pyro5.configure` (or simply :command:`pyro5-check-config`)
   This will print something like::

        Pyro version: 5.10
        Loaded from: /home/irmen/Projects/pyro5/Pyro5
        Python version: CPython 3.8.2 (Linux, posix)
        Protocol version: 502
        Currently active global configuration settings:
        BROADCAST_ADDRS = ['<broadcast>', '0.0.0.0']
        COMMTIMEOUT = 0.0
        COMPRESSION = False
        ...

3. Access the config as a dictionary: ``Pyro5.config.as_dict()``
4. Access the config string dump (used in #2): ``Pyro5.config.dump()``


.. index:: configuration items

.. _config-items:

Overview of Config Items
------------------------

========================= ======= ======================= =======
config item               type    default                 meaning
========================= ======= ======================= =======
COMMTIMEOUT               float   0.0                     Network communication timeout in seconds. 0.0=no timeout (infinite wait)
COMPRESSION               bool    False                   Enable to make Pyro compress the data that travels over the network
DETAILED_TRACEBACK        bool    False                   Enable to get detailed exception tracebacks (including the value of local variables per stack frame)
HOST                      str     localhost               Hostname where Pyro daemons will bind on
MAX_MESSAGE_SIZE          int     1073741824 (1 Gb)       Maximum size in bytes of the messages sent or received on the wire. If a message exceeds this size, a ProtocolError is raised.
NS_HOST                   str     *equal to HOST*         Hostname for the name server. Used for locating in clients only (use the normal HOST config item in the name server itself)
NS_PORT                   int     9090                    TCP port of the name server. Used by the server and for locating in clients.
NS_BCPORT                 int     9091                    UDP port of the broadcast responder from the name server. Used by the server and for locating in clients.
NS_BCHOST                 str     None                    Hostname for the broadcast responder of the name server. Used by the server only.
NS_AUTOCLEAN              float   0.0                     Specify a recurring period in seconds where the Name server checks its registrations and removes the ones that are not available anymore. (0=disabled, otherwise should be >=3)
NS_LOOKUP_DELAY           float   0.0                     The max. number of seconds a name lookup will wait until the name becomes available in the nameserver (client-side retry)
NATHOST                   str     None                    External hostname in case of NAT (used by the server)
NATPORT                   int     0                       External port in case of NAT (used by the server) 0=replicate internal port number as NAT port
BROADCAST_ADDRS           str     <broadcast>, 0.0.0.0    List of comma separated addresses that Pyro should send broadcasts to (for NS locating in clients)
ONEWAY_THREADED           bool    True                    Enable to make oneway calls be processed in their own separate thread
POLLTIMEOUT               float   2.0                     For the multiplexing server only: the timeout of the select or poll calls
SERVERTYPE                str     thread                  Select the Pyro server type. thread=thread pool based, multiplex=select/poll/kqueue based
SOCK_REUSE                bool    True                    Should SO_REUSEADDR be used on sockets that Pyro creates.
SOCK_NODELAY              bool    False                   Use tcp_nodelay on sockets
PREFER_IP_VERSION         int     0                       The IP address type that is preferred (4=ipv4, 6=ipv6, 0=let OS decide).
SERPENT_BYTES_REPR        bool    False                   If True, use Python's repr format to serialize bytes types, rather than the base-64 encoding format.
THREADPOOL_SIZE           int     80                      For the thread pool server: maximum number of threads running
THREADPOOL_SIZE_MIN       int     4                       For the thread pool server: minimum number of threads running
SERIALIZER                str     serpent                 The wire protocol serializer to use for clients/proxies (one of: serpent, json, marshal, msgpack)
LOGWIRE                   bool    False                   If wire-level message data should be written to the logfile (you may want to disable COMPRESSION)
MAX_RETRIES               int     0                       Automatically retry network operations for some exceptions (timeout / connection closed), be careful to use when remote functions have a side effect (e.g.: calling twice results in error)
ITER_STREAMING            bool    True                    Should iterator item streaming support be enabled in the server (default=True)
ITER_STREAM_LIFETIME      float   0.0                     Maximum lifetime in seconds for item streams (default=0, no limit - iterator only stops when exhausted or client disconnects)
ITER_STREAM_LINGER        float   30.0                    Linger time in seconds to keep an item stream alive after proxy disconnects (allows to reconnect to stream)
SSL                       bool    False                   Should SSL/TSL communication security be used? Enabling it also requires some other SSL config items to be set.
SSL_SERVERCERT            str     *empty str*             Location of the server's certificate file
SSL_SERVERKEY             str     *empty str*             Location of the server's private key file
SSL_SERVERKEYPASSWD       str     *empty str*             Password for the server's private key
SSL_REQUIRECLIENTCERT     bool    False                   Should the server require clients to connect with their own certificate (2-way-ssl)
SSL_CLIENTCERT            str     *empty str*             Location of the client's certificate file
SSL_CLIENTKEY             str     *empty str*             Location of the client's private key file
SSL_CLIENTKEYPASSWD       str     *empty str*             Password for the client's private key
SSL_CACERTS               str     *empty str*             Location of a 'CA' signing certificate (or a directory containing these in PEM format, `"following an OpenSSL specific layout" <https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_verify_locations>`_.)
========================= ======= ======================= =======

.. index::
    double: configuration items; logging

There are two special config items that control Pyro's logging, and that are only available as environment variable settings.
This is because they are used at the moment the Pyro5 package is being imported
(which means that modifying them as regular config items after importing Pyro5 is too late and won't work).

It is up to you to set the environment variable you want to the desired value. You can do this from your OS or shell,
or perhaps by modifying ``os.environ`` in your Python code *before* importing Pyro5.


======================= ======= ============== =======
environment variable    type    default        meaning
======================= ======= ============== =======
PYRO_LOGLEVEL           string  *not set*      The log level to use for Pyro's logger (DEBUG, WARN, ...) See Python's standard :py:mod:`logging` module for the allowed values. If it is not set, no logging is being configured.
PYRO_LOGFILE            string  pyro.log       The name of the log file. Use {stderr} to make the log go to the standard error output.
======================= ======= ============== =======
