import timeit
import Pyro4.naming


Pyro4.config.SERIALIZER = 'marshal'


num_iterations = 3000
num_tries = 10

ns = Pyro4.naming.locateNS()
ns._pyroBind()


def test():
    ns.list("Pyro.NameServer", return_metadata=False)


print("running %d tries..." % num_tries)
timer = timeit.Timer("test()", "from __main__ import test")
result = timer.repeat(num_tries, num_iterations)
best = min(result)
print("Best of %d tries: %.0f calls/sec" % (num_tries, num_iterations/best))
