import time
import Pyro4

ns=Pyro4.locateNS()

iterations = 10000
print("PYRO 4 running", iterations, "calls...")

start = time.time()
for _ in range(iterations):
    ns.list()

duration = time.time()-start
print("done! calls/sec: {:.0f}".format(iterations/duration))
