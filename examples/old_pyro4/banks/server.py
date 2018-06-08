#
#   The banks server
#

from __future__ import print_function
from Pyro5.compatibility import Pyro4
import Pyro4
import banks

with Pyro4.Daemon() as daemon:
    with Pyro4.locateNS() as ns:
        uri = daemon.register(banks.Rabobank)
        ns.register("example.banks.rabobank", uri)
        uri = daemon.register(banks.ABN)
        ns.register("example.banks.abn", uri)
        print("available banks:")
        print(list(ns.list(prefix="example.banks.").keys()))

    # enter the service loop.
    print("Banks are ready for customers.")
    daemon.requestLoop()
