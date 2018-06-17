This example shows the use of 'oneway' method calls.

If you flag a method call 'oneway' (with the oneway decorator),
Pyro will not wait for a response from the remote object.
This means that your client program can continue to work,
while the remote object is still busy processing the method call.
(Normal remote method calls are synchronous and will always block until the
remote object is done with the method call).

This example also shows the use of the ONEWAY_THREADED setting in the
server. This setting is OFF by default!

If set to False, the server will process all calls from
the same proxy sequentially (and additional calls will have to wait),
but no unexpected new threads are created.

If set to True, which is done in this example,
it means that oneway method calls are executed in their own
separate thread, so the server remains responsive for additional calls
from the same client even when the oneway call is still running.
This could lead to complex behavior in the server because a new thread is created
to handle the request regardless of the type of server you are running.
But it does allow the client proxy to continue after doing subsequent oneway calls,
as you might expect it to behave with these.
