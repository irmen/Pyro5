import time
import Pyro4

ns = Pyro4.locateNS()

iterations = 20000
print("PYRO 4 running", iterations, "calls...")

start = time.time()
for _ in range(iterations):
    ns.list("Pyro.NameServer", return_metadata=True)

duration = time.time()-start
print("done! calls/sec: {:.0f}".format(iterations/duration))
