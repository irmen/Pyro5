import logging
import sys
from Pyro5.api import expose, callback, Daemon, Proxy


# initialize the logger so you can see what is happening with the callback exception message:
logging.basicConfig(stream=sys.stderr, format="[%(asctime)s,%(name)s,%(levelname)s] %(message)s")
log = logging.getLogger("Pyro5")
log.setLevel(logging.WARNING)


class CallbackHandler(object):
    def crash(self):
        a = 1
        b = 0
        return a // b

    @expose
    def call1(self):
        print("\n\ncallback 1 received from server!")
        print("going to crash - you won't see the exception here, only on the server")
        return self.crash()

    @expose
    @callback
    def call2(self):
        print("\n\ncallback 2 received from server!")
        print("going to crash - but you will see the exception printed here too:")
        return self.crash()


daemon = Daemon()
callback = CallbackHandler()
daemon.register(callback)

with Proxy("PYRONAME:example.callback2") as server:
    server.doCallback(callback)   # this is a oneway call, so we can continue right away

print("waiting for callbacks to arrive...")
print("(ctrl-c/break the program once it's done)")
daemon.requestLoop()
