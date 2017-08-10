import time
import Pyro5.api

ns = Pyro5.api.locateNS()

iterations = 20000
print("PYRO 5 running", iterations, "calls...")

start = time.time()
for _ in range(iterations):
    ns.list("Pyro.NameServer", return_metadata=True)

duration = time.time()-start
print("done! calls/sec: {:.0f}".format(iterations/duration))
