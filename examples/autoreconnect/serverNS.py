import time
from Pyro5.api import expose, Daemon, locate_ns
import Pyro5.errors


print("Autoreconnect using Name Server.")


@expose
class TestClass(object):
    def method(self, arg):
        """
        Print a method

        Args:
            self: (todo): write your description
            arg: (todo): write your description
        """
        print("Method called with %s" % arg)
        print("You can now try to stop this server with ctrl-C/ctrl-Break")
        time.sleep(1)


# If we reconnect the object, it has to have the same objectId as before.
# for this example, we rely on the Name Server registration to get our old id back.
# If we KNOW 100% that PYRONAME-uris are the only thing used to access our
# object, we could skip all this and just register as usual.
# That works because the proxy, when reconnecting, will do a new nameserver lookup
# and receive the new object uri back. This REQUIRES:
#   - clients will never connect using a PYRO-uri
#   - client proxy._pyroBind() is never called
# BUT for sake of example, and because we really cannot guarantee the above,
# here we go for the safe route and reuse our previous object id.

ns = locate_ns()
try:
    existing = ns.lookup("example.autoreconnect")
    print("Object still exists in Name Server with id: %s" % existing.object)
    print("Previous daemon socket port: %d" % existing.port)
    # start the daemon on the previous port
    daemon = Daemon(port=existing.port)
    # register the object in the daemon with the old objectId
    daemon.register(TestClass, objectId=existing.object)
except Pyro5.errors.NamingError:
    print("There was no previous registration in the name server.")
    # just start a new daemon on a random port
    daemon = Daemon()
    # register the object in the daemon and let it get a new objectId
    # also need to register in name server because it's not there yet.
    uri = daemon.register(TestClass)
    ns.register("example.autoreconnect", uri)

print("Server started.")
daemon.requestLoop()

# note: we are not removing the name server registration when terminating!
