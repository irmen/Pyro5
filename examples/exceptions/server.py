from Pyro5.api import Daemon
import excep

Daemon.serveSimple(
    {
        excep.TestClass: "example.exceptions"
    },
    ns=True, verbose=True)
