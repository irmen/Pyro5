from Pyro5.api import Daemon, serve, expose, behavior, current_context


class CustomDaemon(Daemon):
    def clientDisconnect(self, conn):
        # If required, you *can* override this to do custom resource freeing.
        # But this is not needed if your resource objects have a proper 'close' method;
        # this method is called by Pyro itself once the client connection gets closed.
        # In this example this override is only used to print out some info.
        print("client disconnects:", conn.sock.getpeername())
        print("    resources: ", [r.name for r in conn.tracked_resources])


class Resource(object):
    # a fictional resource that gets allocated and must be freed again later.
    def __init__(self, name, collection):
        self.name = name
        self.collection = collection

    def close(self):
        # Pyro will call this on a tracked resource once the client's connection gets closed!
        # (Unless the resource can be carbage collected normally by Python.)
        print("Resource: closing", self.name)
        self.collection.discard(self)


@expose
@behavior(instance_mode="single")
class Service(object):
    def __init__(self):
        self.resources = set()      # the allocated resources

    def allocate(self, name):
        resource = Resource(name, self.resources)
        self.resources.add(resource)
        current_context.track_resource(resource)
        print("service: allocated resource", name, " for client", current_context.client_sock_addr)

    def free(self, name):
        resources = {r for r in self.resources if r.name == name}
        self.resources -= resources
        for r in resources:
            r.close()
            current_context.untrack_resource(r)

    def list(self):
        return [r.name for r in self.resources]


with CustomDaemon() as daemon:
    serve({
        Service: "service"
    }, use_ns=False, daemon=daemon)
