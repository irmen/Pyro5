This example shows how Pyro deals with sharing proxies in different threads.
Pyro does NOT allow you to share the same proxy across different threads,
because concurrent access to the same network connection will likely corrupt the
data sequence.  Pyro's proxy object doesn't have an internal lock to guard against
this - because locks are expensive.  You will have to make sure yourself, that:

- you make sure each thread uses their own new proxy object
- or, you transfer a proxy object from one thread to another.


This example shows both techniques.

You'll have to start a Pyro name server first, before running the client.
