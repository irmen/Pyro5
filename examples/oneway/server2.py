import time
import threading
from Pyro5.api import expose, oneway, behavior, serve


@expose
@behavior("single")
class Server(object):
    def __init__(self):
        """
        Initialize the counter.

        Args:
            self: (todo): write your description
        """
        self.counter = 0

    @oneway
    def increment_oneway(self):
        """
        Increment the counter.

        Args:
            self: (todo): write your description
        """
        print("oneway call executing in thread", threading.get_ident())
        time.sleep(0.5)
        self.counter += 1

    def increment(self):
        """
        Increment counter.

        Args:
            self: (todo): write your description
        """
        time.sleep(0.5)
        self.counter += 1

    def getcount(self):
        """
        Return the number of times.

        Args:
            self: (todo): write your description
        """
        return self.counter


print("main thread:", threading.get_ident())
serve({
    Server: "example.oneway2"
})
