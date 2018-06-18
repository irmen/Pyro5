import time
from Pyro5.api import Proxy


with Proxy("PYRONAME:example.oneway2") as serv:
    print("incrementing a few times normally")
    serv.increment()
    serv.increment()
    serv.increment()
    counter = serv.getcount()
    print("counter in server is now: ", counter)
    print("incrementing a few times via oneway call (should be almost instantaneous)")
    serv.increment_oneway()
    serv.increment_oneway()
    serv.increment_oneway()
    counter2 = serv.getcount()
    print("counter is now: ", counter2)
    if counter2 == counter:
        print("ok, the oneway calls are still being processed in the background.")
        print("   we'll wait a bit till they're done...")
        time.sleep(2)
        counter2 = serv.getcount()
        print("counter is now: ", counter2)
    else:
        raise SystemExit("!? the oneway calls have not been processed in the background!?")
