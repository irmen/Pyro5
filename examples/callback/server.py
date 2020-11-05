import time
from Pyro5.api import expose, oneway, serve


class Worker(object):
    def __init__(self, number, callback):
        """
        Initialize the callback.

        Args:
            self: (todo): write your description
            number: (int): write your description
            callback: (callable): write your description
        """
        self.number = number
        self.callback = callback
        print("Worker %d created" % self.number)

    @expose
    @oneway
    def work(self, amount):
        """
        Unregister a new work.

        Args:
            self: (todo): write your description
            amount: (int): write your description
        """
        print("Worker %d busy..." % self.number)
        time.sleep(amount)
        print("Worker %d done. Informing callback client." % self.number)
        self._pyroDaemon.unregister(self)
        self.callback._pyroClaimOwnership()     # because this method may run in a different thread every time it's called
        self.callback.done(self.number)  # invoke the callback object


class CallbackServer(object):
    def __init__(self):
        """
        Initialize the internal state.

        Args:
            self: (todo): write your description
        """
        self.number = 0

    @expose
    def addworker(self, callback):
        """
        Add a worker.

        Args:
            self: (todo): write your description
            callback: (todo): write your description
        """
        self.number += 1
        print("server: adding worker %d" % self.number)
        worker = Worker(self.number, callback)
        self._pyroDaemon.register(worker)  # make it a Pyro object
        return worker


serve({
    CallbackServer: "example.callback"
})
