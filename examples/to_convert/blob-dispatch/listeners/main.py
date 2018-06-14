import sys
from Pyro5.compatibility import Pyro4
import Pyro4
from listener import Listener


if len(sys.argv) != 2:
    print("Give topic as argument.")
else:
    topic = sys.argv[1].strip()
    if not topic:
        raise ValueError("Must give topic name.")
    listener = Listener(topic)
    daemon = Pyro4.Daemon()
    daemon.register(listener)
    listener.register_with_dispatcher()
    print("Listener for topic {} waiting for data.".format(topic))
    daemon.requestLoop()
