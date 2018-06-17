import Pyro5.api
import chain


this_node = "B"
next_node = "C"

servername = "example.chain." + this_node

with Pyro5.api.Daemon() as daemon:
    obj = chain.Chain(this_node, next_node)
    uri = daemon.register(obj)
    with Pyro5.api.locate_ns() as ns:
        ns.register(servername, uri)

    # enter the service loop.
    print("Server started %s" % this_node)
    daemon.requestLoop()
