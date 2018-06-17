import time
import threading
import Pyro5.api
import Pyro5.errors


proxy = Pyro5.api.locate_ns()    # grab a proxy for the name server


print("Main thread:", threading.current_thread())
proxy.ping()    # call it, the proxy is now connected and bound to the main thread


# trying to use the proxy in a different thread is not possible,
# and Pyro will raise an exception to tell you that:

def other_thread_call():
    try:
        proxy.ping()
        print("You should not see this!! the call succeeded in thread", threading.current_thread())
    except Pyro5.errors.PyroError as x:
        print("Expected exception in thread", threading.current_thread())
        print("Exception was: ", x)


print()
threading.Thread(target=other_thread_call).start()
time.sleep(1)


# SOLUTION 1:  create a new proxy in the other thread.

def new_proxy_thread_call(uri):
    proxy = Pyro5.api.Proxy(uri)
    proxy.ping()
    print("Solution 1. The call succeeded in thread", threading.current_thread())


print()
threading.Thread(target=new_proxy_thread_call, args=(proxy._pyroUri,)).start()
time.sleep(1)


# SOLUTION 2:  transfer ownership of our proxy to the other thread.

def new_owner_thread_call(proxy):
    proxy._pyroClaimOwnership()
    proxy.ping()
    print("Solution 2. The call succeeded in thread", threading.current_thread())


print()
threading.Thread(target=new_owner_thread_call, args=(proxy,)).start()
time.sleep(1)


# however, we are no longer the owner of the proxy now, so any new calls will fail for us
print()
try:
    proxy.ping()
    print("You should not see this!! the call succeeded in thread", threading.current_thread())
except Pyro5.errors.PyroError as x:
    print("Expected exception in thread", threading.current_thread())
    print("Exception was: ", x)
