import sys
import random
import time
import threading
import contextlib
from Pyro5.api import Proxy, locate_ns
import Pyro5.errors


def randomname():
    def partname():
        return str(random.random())[-2:]

    parts = ["stresstest"]
    for i in range(random.randint(1, 10)):
        parts.append(partname())
    return ".".join(parts)


class NamingTrasher(threading.Thread):
    def __init__(self, nsuri, number):
        threading.Thread.__init__(self)
        self.daemon = True
        self.number = number
        self.ns = Proxy(nsuri)
        self.mustStop = False

    def list(self):
        items = self.ns.list()

    def register(self):
        for i in range(4):
            with contextlib.suppress(Pyro5.errors.NamingError):
                self.ns.register(randomname(), 'PYRO:objname@host:555')

    def remove(self):
        self.ns.remove(randomname())

    def lookup(self):
        with contextlib.suppress(Pyro5.errors.NamingError):
            uri = self.ns.lookup(randomname())

    def listprefix(self):
        entries = self.ns.list(prefix="stresstest.51")

    def listregex(self):
        entries = self.ns.list(regex=r"stresstest\.??\.41.*")

    def run(self):
        print("Name Server trasher running.")
        self.ns._pyroClaimOwnership()
        while not self.mustStop:
            random.choice((self.list, self.register, self.remove, self.lookup, self.listregex, self.listprefix))()
            sys.stdout.write("%d " % self.number)
            sys.stdout.flush()
            time.sleep(0.001)
        print("Trasher exiting.")


def main():
    threads = []
    ns = locate_ns()
    print("Removing previous stresstest registrations...")
    ns.remove(prefix="stresstest.")
    print("Done. Starting.")
    for i in range(5):
        nt = NamingTrasher(ns._pyroUri, i)
        nt.start()
        threads.append(nt)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    print("Break-- waiting for threads to stop.")
    for nt in threads:
        nt.mustStop = True
        nt.join()
    count = ns.remove(prefix="stresstest.")
    print("cleaned up %d names." % count)


if __name__ == '__main__':
    main()
