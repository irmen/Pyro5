import logging
from Pyro5.api import expose, serve, config


logging.basicConfig(level=logging.DEBUG)
logging.getLogger("Pyro5").setLevel(logging.DEBUG)

config.COMMTIMEOUT = 5.0
config.POLLTIMEOUT = 5.0  # only used for multiplexing server


class TestDisconnect(object):
    @expose
    def echo(self, arg):
        print("echo: ", arg)
        return arg


serve({
    TestDisconnect: "example.disconnect"
}, use_ns=False)
