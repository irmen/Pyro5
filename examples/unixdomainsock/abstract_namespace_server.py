# this only works on Linux
# it uses the abstract namespace socket feature.

from Pyro5.api import expose, Daemon


@expose
class Thingy(object):
    def message(self, arg):
        """
        Print a message

        Args:
            self: (todo): write your description
            arg: (str): write your description
        """
        print("Message received:", arg)
        return "Roger!"


with Daemon(unixsocket="\0example_unix.sock") as d:   # notice the 0-byte at the start
    uri = d.register(Thingy, "example.unixsock")
    print("Server running, uri=", uri)
    string_uri = str(uri)
    print("Actually, the uri contains a 0-byte, make sure you copy the part between the quotes to the client:")
    print(repr(string_uri))
    d.requestLoop()
