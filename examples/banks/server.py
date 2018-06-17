#
#   The banks server
#

from Pyro5.api import Daemon, locate_ns
import banks


with Daemon() as daemon:
    with locate_ns() as ns:
        uri = daemon.register(banks.Rabobank)
        ns.register("example.banks.rabobank", uri)
        uri = daemon.register(banks.ABN)
        ns.register("example.banks.abn", uri)
        print("available banks:")
        print(list(ns.list(prefix="example.banks.").keys()))

    # enter the service loop.
    print("Banks are ready for customers.")
    daemon.requestLoop()
