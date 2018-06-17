import time
import threading
from Pyro5.api import expose, behavior, oneway, Daemon
import Pyro5.config


@expose
@behavior(instance_mode="single")
class Server(object):
    def __init__(self):
        self.callcount = 0

    def reset(self):
        self.callcount = 0

    def getcount(self):
        return self.callcount  # the number of completed calls

    def getconfig(self):
        return Pyro5.config.as_dict()

    def delay(self):
        threadname = threading.current_thread().getName()
        print("delay called in thread %s" % threadname)
        time.sleep(1)
        self.callcount += 1
        return threadname

    @oneway
    def onewaydelay(self):
        threadname = threading.current_thread().getName()
        print("onewaydelay called in thread %s" % threadname)
        time.sleep(1)
        self.callcount += 1


# main program

Pyro5.config.SERVERTYPE = "undefined"
servertype = input("Servertype threaded or multiplex (t/m)?")
if servertype == "t":
    Pyro5.config.SERVERTYPE = "thread"
else:
    Pyro5.config.SERVERTYPE = "multiplex"


Daemon.serveSimple({
    Server: "example.servertypes"
})
