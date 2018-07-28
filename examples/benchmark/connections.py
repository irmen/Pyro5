import time
from Pyro5.api import Proxy, config


uri = input("Uri of benchmark server? ").strip()

print("Timing raw connect speed (no method call)...")
p = Proxy(uri)
p.oneway()
ITERATIONS = 2000
begin = time.time()
for loop in range(ITERATIONS):
    if loop % 500 == 0:
        print(loop)
    p._pyroRelease()
    p._pyroBind()
duration = time.time() - begin
print("%d connections in %.3f sec = %.0f conn/sec" % (ITERATIONS, duration, ITERATIONS / duration))
del p

print("Timing proxy creation+connect+methodcall speed...")
ITERATIONS = 2000
begin = time.time()
for loop in range(ITERATIONS):
    if loop % 500 == 0:
        print(loop)
    with Proxy(uri) as p:
        p.oneway()
duration = time.time() - begin
print("%d new proxy calls in %.3f sec = %.0f calls/sec" % (ITERATIONS, duration, ITERATIONS / duration))

print("Timing oneway proxy methodcall speed...")
p = Proxy(uri)
p.oneway()
ITERATIONS = 10000
begin = time.time()
for loop in range(ITERATIONS):
    if loop % 1000 == 0:
        print(loop)
    p.oneway()
duration = time.time() - begin
print("%d calls in %.3f sec = %.0f calls/sec" % (ITERATIONS, duration, ITERATIONS / duration))
print("Serializer used:", config.SERIALIZER)
