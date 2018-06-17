import os
from Pyro5.api import expose, Daemon


@expose
class Thingy(object):
    def message(self, arg):
        print("Message received:", arg)
        return "Roger!"


if os.path.exists("example_unix.sock"):
    os.remove("example_unix.sock")

with Daemon(unixsocket="example_unix.sock") as d:
    uri = d.register(Thingy, "example.unixsock")
    print("Server running, uri=", uri)
    d.requestLoop()
