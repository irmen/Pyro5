.. index:: exceptions, remote traceback

********************************
Exceptions and remote tracebacks
********************************

There is an example that shows various ways to deal with exceptions when writing Pyro code.
Have a look at the ``exceptions`` example in the :file:`examples` directory.

Pyro exceptions
---------------

Pyro's exception classes can be found in :mod:`Pyro5.errors`.
They are used by Pyro itself if something went wrong inside Pyro itself or related to something Pyro was doing.
All errors are of type ``PyroError`` or a subclass thereof.

.. index:: remote errors

Remote exceptions
-----------------
More interesting are how Pyro treats exeptions that occur in *your own* objects (the remote Pyro objects):
it is making the remote objects appear as normal, local, Python objects.
That also means that if they raise an error, Pyro will make it appear in the caller (client progam),
as if the error occurred locally at the point of the call.

Assume you have a remote object that can divide arbitrary numbers.
It will raise a ``ZeroDivisionError`` when using 0 as the divisor.
This can be dealt with by just catching the exception as if you were writing regular code::

    import Pyro5.api

    divider=Pyro5.api.Proxy( ... )
    try:
        result = divider.div(999,0)
    except ZeroDivisionError:
        print("yup, it crashed")


Since the error occurred in a *remote* object, and Pyro itself raises it again on the client
side, some information is initially lost: the actual traceback of the crash itself in the server code.
Pyro stores the traceback information on a special attribute on the exception
object (``_pyroTraceback``), as a list of strings (each is a line from
the traceback text, including newlines). You can use this data on the client to print or process the
traceback text from the exception as it occurred in the Pyro object on the server.

There is a utility function in :mod:`Pyro5.errors` to make it easy to deal with this:
:func:`Pyro5.errors.get_pyro_traceback`

You use it like this::

    import Pyro5.errors
    try:
        result = proxy.method()
    except Exception:
        print("Pyro traceback:")
        print("".join(Pyro5.errors.get_pyro_traceback()))


.. index:: exception hook

Also, there is another function that you can install in ``sys.excepthook``, if you want Python
to automatically print the complete Pyro traceback including the remote traceback, if any:
:func:`Pyro5.errors.excepthook`

A full Pyro exception traceback, including the remote traceback on the server, looks something like this::

    Traceback (most recent call last):
      File "client.py", line 54, in <module>
        print(test.complexerror())  # due to the excepthook, the exception will show the pyro error
      File "/home/irmen/Projects/pyro5/Pyro5/client.py", line 476, in __call__
        return self.__send(self.__name, args, kwargs)
      File "/home/irmen/Projects/pyro5/Pyro5/client.py", line 243, in _pyroInvoke
        raise data  # if you see this in your traceback, you should probably inspect the remote traceback as well
    TypeError: unsupported operand type(s) for //: 'str' and 'int'
     +--- This exception occured remotely (Pyro) - Remote traceback:
     | Traceback (most recent call last):
     |   File "/home/irmen/Projects/pyro5/Pyro5/server.py", line 466, in handleRequest
     |     data = method(*vargs, **kwargs)  # this is the actual method call to the Pyro object
     |   File "/home/irmen/Projects/pyro5/examples/exceptions/excep.py", line 24, in complexerror
     |     x.crash()
     |   File "/home/irmen/Projects/pyro5/examples/exceptions/excep.py", line 32, in crash
     |     self.crash2('going down...')
     |   File "/home/irmen/Projects/pyro5/examples/exceptions/excep.py", line 36, in crash2
     |     x = arg // 2
     | TypeError: unsupported operand type(s) for //: 'str' and 'int'
     +--- End of remote traceback


As you can see, the first part is only the exception as it occurs locally on the client (raised
by Pyro). The indented part marked with 'Remote traceback' is the exception as it occurred
in the remote Pyro object.


.. index:: traceback information

Detailed traceback information
------------------------------

There is another utility that Pyro has to make it easier to debug remote object exceptions.
If you enable the ``DETAILED_TRACEBACK`` config item on the server (see :ref:`config-items`), the remote
traceback is extended with details of the values of the local variables in every frame::

     +--- This exception occured remotely (Pyro) - Remote traceback:
     | ----------------------------------------------------
     |  EXCEPTION <class 'TypeError'>: unsupported operand type(s) for //: 'str' and 'int'
     |  Extended stacktrace follows (most recent call last)
     | ----------------------------------------------------
     | File "/home/irmen/Projects/pyro5/Pyro5/server.py", line 466, in Daemon.handleRequest
     | Source code:
     |     data = method(*vargs, **kwargs)  # this is the actual method call to the Pyro object
     | ----------------------------------------------------
     | File "/home/irmen/Projects/pyro5/examples/exceptions/excep.py", line 24, in TestClass.complexerror
     | Source code:
     |     x.crash()
     | Local values:
     |     self = <excep.TestClass object at 0x7f8dec533b20>
     |     x = <excep.Foo object at 0x7f8dec550f40>
     | ----------------------------------------------------
     | File "/home/irmen/Projects/pyro5/examples/exceptions/excep.py", line 32, in Foo.crash
     | Source code:
     |     self.crash2('going down...')
     | Local values:
     |     self = <excep.Foo object at 0x7f8dec550f40>
     | ----------------------------------------------------
     | File "/home/irmen/Projects/pyro5/examples/exceptions/excep.py", line 36, in Foo.crash2
     | Source code:
     |     x = arg // 2
     | Local values:
     |     arg = 'going down...'
     |     self = <excep.Foo object at 0x7f8dec550f40>
     | ----------------------------------------------------
     |  EXCEPTION <class 'TypeError'>: unsupported operand type(s) for //: 'str' and 'int'
     | ----------------------------------------------------
     +--- End of remote traceback


You can immediately see why the call produced a ``TypeError`` without the need to have a debugger running
(the ``arg`` variable is a string and dividing that string by 2 is the cause of the error).
