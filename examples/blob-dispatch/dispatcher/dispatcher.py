from collections import defaultdict
from Pyro5.api import behavior, expose, serve

# note: the dispatcher doesn't know anything about the CustomData class from the customdata module!


@behavior(instance_mode="single")
class Dispatcher(object):
    def __init__(self):
        self.listeners = defaultdict(list)

    @expose
    def register(self, topic, listener):
        self.listeners[topic].append(listener)
        print("New listener for topic {} registered: {}".format(topic, listener._pyroUri))

    @expose
    def process_blob(self, blob):
        print("Dispatching blob with name:", blob.info)
        listeners = self.listeners.get(blob.info, [])
        for listener in listeners:
            listener._pyroClaimOwnership()     # because this process_blob call may run in a different thread every time it is invoked
            listener.process_blob(blob)


serve({
    Dispatcher: "example.blobdispatcher"
})
