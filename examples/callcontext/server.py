import Pyro5.api
import threading


@Pyro5.api.expose
class EchoServer(object):
    def echo(self, message):
        ctx = Pyro5.api.current_context
        print("\nGot Message:", message)
        print("  thread: ", threading.current_thread().ident)
        print("  obj.pyroid: ", self._pyroId)
        print("  obj.daemon: ", self._pyroDaemon)
        print("  context.client: ", ctx.client)
        print("  context.client_sock_addr: ", ctx.client_sock_addr)
        print("  context.seq: ", ctx.seq)
        print("  context.msg_flags: ", ctx.msg_flags)
        print("  context.serializer_id: ", ctx.serializer_id)
        print("  context.correlation_id:", ctx.correlation_id)
        if "XYZZ" in ctx.annotations:
            print("  custom annotation 'XYZZ':", bytes(ctx.annotations["XYZZ"]))
        return message

    @Pyro5.api.oneway
    def oneway(self, message):
        return self.echo(message)


class CustomDaemon(Pyro5.api.Daemon):
    def annotations(self):
        return {"DDAA": b"custom response annotation set by the daemon"}


with CustomDaemon() as daemon:
    uri = daemon.register(EchoServer, "example.context")  # provide a logical name ourselves
    print("Server is ready. You can use the following URI to connect:")
    print(uri)
    daemon.requestLoop()
