import socket
import time
import Pyro5.socketutil
import Pyro5.api


Pyro5.config.SERVERTYPE = "multiplex"
Pyro5.config.POLLTIMEOUT = 3


hostname = socket.gethostname()
my_ip = Pyro5.socketutil.get_ip_address(None, workaround127=True)


@Pyro5.api.expose
class EmbeddedServer(object):
    def multiply(self, x, y):
        return x * y


print("MULTIPLEXED server type. Initializing services...")
print("Make sure that you don't have a name server running already!\n")
# start a name server with broadcast server
nameserverUri, nameserverDaemon, broadcastServer = Pyro5.nameserver.start_ns(host=my_ip)
assert broadcastServer is not None, "expect a broadcast server to be created"
print("got a Nameserver, uri=%s" % nameserverUri)

# create a Pyro daemon
pyrodaemon = Pyro5.api.Daemon(host=hostname)
serveruri = pyrodaemon.register(EmbeddedServer())
print("server uri=%s" % serveruri)

# register it with the embedded nameserver
nameserverDaemon.nameserver.register("example.eventloop.server", serveruri)

print("")

# Because this server runs the different daemons using the "multiplex" server type,
# we can use the built in support (since Pyro 4.44) to combine multiple daemon event loops.
# We can then simply run the event loop of the 'master daemon'. It will dispatch correctly.

pyrodaemon.combine(nameserverDaemon)
pyrodaemon.combine(broadcastServer)


def loopcondition():
    print(time.asctime(), "Waiting for requests...")
    return True


pyrodaemon.requestLoop(loopcondition)

# clean up
nameserverDaemon.close()
broadcastServer.close()
pyrodaemon.close()
print("done")
