import Pyro5.errors
import Pyro5.api


huge_object = [42] * 10000
simple_object = {"message": "hello", "irrelevant": huge_object}

print("First start the built-in test echo server with something like:")
print("$ python -m Pyro5.utils.echoserver")
print("Enter the server's uri that was printed:")
uri = input().strip()
echoserver = Pyro5.api.Proxy(uri)

Pyro5.config.MAX_MESSAGE_SIZE = 2**32
print("\nSending big data with virtually no limit on message size...")
response = echoserver.echo(simple_object)
print("success.")

try:
    Pyro5.config.MAX_MESSAGE_SIZE = 2500
    print("\nSending big data with a limit on message size...")
    response = echoserver.echo(simple_object)
    print("Hmm, this should have raised an exception")
except Pyro5.errors.MessageTooLargeError as x:
    print("EXCEPTION (expected):", x)
