from Pyro5.compatibility import Pyro4
import Pyro4
import chain


this_node = "C"
next_node = "A"

servername = "example.chain." + this_node

with Pyro4.Daemon() as daemon:
    obj = chain.Chain(this_node, next_node)
    uri = daemon.register(obj)
    with Pyro4.locateNS() as ns:
        ns.register(servername, uri)

    # enter the service loop.
    print("Server started %s" % this_node)
    daemon.requestLoop()
