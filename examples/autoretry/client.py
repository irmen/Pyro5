from time import sleep
import Pyro5.api


# client side will not have timeout
Pyro5.config.COMMTIMEOUT = 0

# Not using auto-retry feature
Pyro5.config.MAX_RETRIES = 0

obj = Pyro5.api.Proxy("PYRONAME:example.autoretry")
print("Calling remote function 1st time (create connection)")
obj.add(1, 1)
print("Calling remote function 2nd time (not timed out yet)")
obj.add(2, 2)
print("Sleeping 1 second...")
sleep(1)
print("Calling remote function 3rd time (will raise an exception)")
try:
    obj.add(3, 3)
except Exception as e:
    print("Got exception %r as expected." % repr(e))

print("\nNow, let's enable the auto retry on the proxy")
obj._pyroRelease()
obj._pyroMaxRetries = 2

print("Calling remote function 1st time (create connection)")
obj.add(1, 1)
print("Calling remote function 2nd time (not timed out yet)")
obj.add(2, 2)
print("Sleeping 1 second...")
sleep(1)
print("Calling remote function 3rd time (will not raise any exceptions)")
obj.add(3, 3)
