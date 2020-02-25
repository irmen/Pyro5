An example of using Pyro to implement a form of privilege separation
http://en.wikipedia.org/wiki/Privilege_separation

One server provides an api to access a part of the system by regular client code
that would normally require elevated privileges. In this case you only need to run
the confined server with elevated privileges, and the client code can run with
normal user level privileges. Such a server should only expose just that tiny bit
of functionality that requires the elevated privileges. This then avoids having to run
the entire program (the client in this case) as an elevated user.


The other example does the opposite: the server drops privileges after it started
to voluntarily make it more restrictive in what it can do.
This is used to mitigate the potential damage of a computer security vulnerability.
The way it's done here is rather primitive, but it works. It just switches uid/gid to 'nobody'.
If you're using Linux, there are more sophisticated ways to do this.
For example see https://deescalate.readthedocs.io/en/latest/
The example client calls the server to perform an operation but the dropped privileges
will now prevent the server from carrying out the request if it is not allowed to do so.


This example was developed on a Linux system. It should work on MacOS as well,
but is not compatible with Windows. You can still get the idea though.
