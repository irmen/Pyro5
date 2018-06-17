import logging
from Pyro5.api import expose, Daemon
import Pyro5.config


logging.basicConfig(level=logging.DEBUG)
logging.getLogger("Pyro5").setLevel(logging.DEBUG)

Pyro5.config.COMMTIMEOUT = 5.0
Pyro5.config.POLLTIMEOUT = 5.0  # only used for multiplexing server


class TestDisconnect(object):
    @expose
    def echo(self, arg):
        print("echo: ", arg)
        return arg


Daemon.serveSimple({
    TestDisconnect: "example.disconnect"
}, ns=False)
