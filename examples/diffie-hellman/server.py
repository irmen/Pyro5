from Pyro5.api import behavior, expose, locate_ns, Daemon, config
from diffiehellman import DiffieHellman


config.SERVERTYPE = "multiplex"

ns = locate_ns()


@behavior(instance_mode="session")
class KeyExchange(object):
    def __init__(self):
        print("New KeyExchange, initializing Diffie-Hellman")
        self.dh = DiffieHellman(group=14)

    @expose
    def exchange_key(self, other_public_key):
        print("received a public key, calculating shared secret...")
        self.dh.make_shared_secret_and_key(other_public_key)
        print("shared secret key = ", self.dh.key.hex())
        return self.dh.public_key


Daemon.serveSimple({
    KeyExchange: "example.dh.keyexchange"
}, ns=True)
