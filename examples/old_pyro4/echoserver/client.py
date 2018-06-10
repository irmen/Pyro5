from Pyro5.compatibility import Pyro4
import Pyro4
import Pyro4.util


print("First start the built-in test echo server with something like:")
print("$ python -m Pyro4.test.echoserver")
print("Enter the server's uri that was printed:")
uri = input().strip()
echoserver = Pyro4.Proxy(uri)

response = echoserver.echo("hello")
print("\ngot back from the server: %s" % response)
response = echoserver.echo([1, 2, 3, 4])
print("got back from the server: %s" % response)

for element in echoserver.generator():
    print("got element from remote iterator:", element)

try:
    echoserver.error()
except:
    print("\ncaught an exception (expected), traceback:")
    print("".join(Pyro4.util.getPyroTraceback()))

print("\nshutting down the test echo server. (restart it if you want to run this again)")
echoserver.shutdown()
