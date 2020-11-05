import os
import socket
from math import sqrt
from Pyro5.api import expose, Daemon, locate_ns
import Pyro5.socketutil


class Worker(object):
    @expose
    def factorize(self, n):
        """
        Factorize n times.

        Args:
            self: (todo): write your description
            n: (array): write your description
        """
        print("factorize request received for", n)
        result = self._factorize(n)
        print("    -->", result)
        return result

    def _factorize(self, n):
        """simple algorithm to find the prime factorials of the given number n"""

        def isPrime(n):
            """
            Returns true if n is equal false otherwise false.

            Args:
                n: (int): write your description
            """
            return not any(x for x in range(2, int(sqrt(n)) + 1) if n % x == 0)

        primes = []
        candidates = range(2, n + 1)
        candidate = 2
        while not primes and candidate in candidates:
            if n % candidate == 0 and isPrime(candidate):
                primes = primes + [candidate] + self._factorize(n // candidate)
            candidate += 1
        return primes


with Daemon(host=Pyro5.socketutil.get_ip_address(None)) as daemon:
    # create a unique name for this worker (otherwise it overwrites other workers in the name server)
    worker_name = "Worker_%d@%s" % (os.getpid(), socket.gethostname())
    print("Starting up worker", worker_name)
    uri = daemon.register(Worker)
    with locate_ns() as ns:
        ns.register(worker_name, uri, metadata={"example3.worker.factorizer"})
    daemon.requestLoop()
