import time
import threading
from Pyro5.api import expose, behavior, oneway, serve, config


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
        return config.as_dict()

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

config.SERVERTYPE = "undefined"
servertype = input("Servertype threaded or multiplex (t/m)?")
if servertype == "t":
    config.SERVERTYPE = "thread"
else:
    config.SERVERTYPE = "multiplex"


serve({
    Server: "example.servertypes"
})
