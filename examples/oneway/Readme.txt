This example shows the use of 'oneway' method calls.

If you flag a method call 'oneway' (with the oneway decorator),
Pyro will not wait for a response from the remote object.
This means that your client program can continue to work,
while the remote object is still busy processing the method call.
(Normal remote method calls are synchronous and will always block until the
remote object is done with the method call).

Oneway method calls are executed in their own
separate thread, so the server remains responsive for additional calls
from the same client even when the oneway call is still running.
This may lead to complex behavior in the server because a new thread is created
to handle the request regardless of the type of server you are running.
But it does allow the client proxy to continue after doing subsequent oneway calls,
as you might expect it to behave with these.
