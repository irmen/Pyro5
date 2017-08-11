import timeit
import uuid
import Pyro4
import Pyro4.core


# Pyro4.core.current_context.correlation_id = uuid.uuid1()

num_iterations = 3000
num_tries = 10

ns = Pyro4.locateNS()
ns._pyroBind()


def test():
    ns.list("Pyro.NameServer", return_metadata=True)


print("running %d tries..." % num_tries)
timer = timeit.Timer("test()", "from __main__ import test")
result = timer.repeat(num_tries, num_iterations)
best = min(result)
print("Best of %d tries: %.0f calls/sec" % (num_tries, num_iterations/best))
