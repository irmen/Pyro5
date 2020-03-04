from Pyro5.api import expose, oneway, serve
import Pyro5.errors


class CallbackServer(object):
    @expose
    @oneway
    def doCallback(self, callback):
        print("\n\nserver: doing callback 1 to client")
        callback._pyroClaimOwnership()
        try:
            callback.call1()
        except Exception:
            print("got an exception from the callback:")
            print("".join(Pyro5.errors.get_pyro_traceback()))
        print("\n\nserver: doing callback 2 to client")
        try:
            callback.call2()
        except Exception:
            print("got an exception from the callback:")
            print("".join(Pyro5.errors.get_pyro_traceback()))
        print("server: callbacks done.\n")


serve({
    CallbackServer: "example.callback2"
})
