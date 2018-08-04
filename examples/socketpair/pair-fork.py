# this example forks() and thus won't work on Windows.

import os
import signal
import socket
from Pyro5.api import Daemon, Proxy, expose


# create our own socket pair (server-client sockets that are already connected)
sock1, sock2 = socket.socketpair()

pid = os.fork()

if pid == 0:
    # we are the child process, we host the daemon.

    class Echo(object):
        @expose
        def echo(self, message):
            print("server got message: ", message)
            return "thank you"

    # create a daemon with some Pyro object running on our custom server socket
    daemon = Daemon(connected_socket=sock1)
    daemon.register(Echo, "echo")
    print("Process PID={:d}: Pyro daemon running on {:s}\n".format(os.getpid(), daemon.locationStr))
    daemon.requestLoop()

else:
    # we are the parent process, we create a Pyro client proxy
    print("Process PID={:d}: Pyro client.\n".format(os.getpid()))

    # create a client running on the client socket
    with Proxy("echo", connected_socket=sock2) as p:
        reply = p.echo("hello!")
        print("client got reply:", reply)
        reply = p.echo("hello again!")
        print("client got reply:", reply)
    with Proxy("echo", connected_socket=sock2) as p:
        reply = p.echo("hello2!")
        print("client got reply:", reply)
        reply = p.echo("hello2 again!")
        print("client got reply:", reply)

    os.kill(pid, signal.SIGTERM)
    os.waitpid(pid, 0)
    print("\nThe end.")
