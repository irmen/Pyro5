import logging
from Pyro5.compatibility import Pyro4
import Pyro4


logging.basicConfig(level=logging.DEBUG)
logging.getLogger("Pyro5").setLevel(logging.DEBUG)

Pyro4.config.COMMTIMEOUT = 5.0
Pyro4.config.POLLTIMEOUT = 5.0  # only used for multiplexing server


class TestDisconnect(object):
    @Pyro4.expose
    def echo(self, arg):
        print("echo: ", arg)
        return arg


Pyro4.Daemon.serveSimple({
    TestDisconnect: "example.disconnect"
}, ns=False)
