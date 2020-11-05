from collections import defaultdict
from Pyro5.api import behavior, expose, serve

# note: the dispatcher doesn't know anything about the CustomData class from the customdata module!


@behavior(instance_mode="single")
class Dispatcher(object):
    def __init__(self):
        """
        Initialize the default configuration.

        Args:
            self: (todo): write your description
        """
        self.listeners = defaultdict(list)

    @expose
    def register(self, topic, listener):
        """
        Register a listener for a listener.

        Args:
            self: (todo): write your description
            topic: (str): write your description
            listener: (list): write your description
        """
        self.listeners[topic].append(listener)
        print("New listener for topic {} registered: {}".format(topic, listener._pyroUri))

    @expose
    def process_blob(self, blob):
        """
        Process blob.

        Args:
            self: (todo): write your description
            blob: (todo): write your description
        """
        print("Dispatching blob with name:", blob.info)
        listeners = self.listeners.get(blob.info, [])
        for listener in listeners:
            listener._pyroClaimOwnership()     # because this process_blob call may run in a different thread every time it is invoked
            listener.process_blob(blob)


serve({
    Dispatcher: "example.blobdispatcher"
})
