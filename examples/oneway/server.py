import time
from Pyro5.api import expose, oneway, serve


@expose
class Server(object):
    def __init__(self):
        """
        Initialize the bus.

        Args:
            self: (todo): write your description
        """
        self.busy = False

    @oneway
    def oneway_start(self, duration):
        """
        Disables the bus.

        Args:
            self: (todo): write your description
            duration: (float): write your description
        """
        print("start request received. Starting work...")
        self.busy = True
        for i in range(duration):
            time.sleep(1)
            print(duration - i)
        print("work is done!")
        self.busy = False

    def ready(self):
        """
        Check if the bus has been ready.

        Args:
            self: (todo): write your description
        """
        print("ready status requested (%r)" % (not self.busy))
        return not self.busy

    def result(self):
        """
        Returns the result.

        Args:
            self: (todo): write your description
        """
        return "The result :)"

    def nothing(self):
        """
        Displays the current working directory

        Args:
            self: (todo): write your description
        """
        print("nothing got called, doing nothing")

    @oneway
    def oneway_work(self):
        """
        Prints the number of the work.

        Args:
            self: (todo): write your description
        """
        for i in range(10):
            print("work work..", i+1)
            time.sleep(1)
        print("work's done!")


serve({
    Server: "example.oneway"
})
