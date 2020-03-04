import time
from Pyro5.api import expose, oneway, serve


@expose
class Server(object):
    def __init__(self):
        self.busy = False

    @oneway
    def oneway_start(self, duration):
        print("start request received. Starting work...")
        self.busy = True
        for i in range(duration):
            time.sleep(1)
            print(duration - i)
        print("work is done!")
        self.busy = False

    def ready(self):
        print("ready status requested (%r)" % (not self.busy))
        return not self.busy

    def result(self):
        return "The result :)"

    def nothing(self):
        print("nothing got called, doing nothing")

    @oneway
    def oneway_work(self):
        for i in range(10):
            print("work work..", i+1)
            time.sleep(1)
        print("work's done!")


serve({
    Server: "example.oneway"
})
