import time
import Pyro5.api
import Pyro5.errors


print("Autoreconnect using PYRO uri.")

# We create a proxy with a PYRO uri.
# Reconnect logic depends on the server now.
# (it needs to restart the object with the same id)
uri = input("Enter the uri that the server printed:").strip()
obj = Pyro5.api.Proxy(uri)

while True:
    print("call...")
    try:
        obj.method(42)
        print("Sleeping 1 second")
        time.sleep(1)
    except Pyro5.errors.ConnectionClosedError:  # or possibly CommunicationError
        print("Connection lost. REBINDING...")
        print("(restart the server now)")
        obj._pyroReconnect()
