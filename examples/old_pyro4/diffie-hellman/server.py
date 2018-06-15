from Pyro5.compatibility import Pyro4
import Pyro4
import Pyro4.errors
import Pyro5.api
from diffiehellman import DiffieHellman


Pyro4.config.SERVERTYPE = "multiplex"

ns = Pyro4.locateNS()


@Pyro4.behavior(instance_mode="session")
class KeyExchange(object):
    def __init__(self):
        print("New KeyExchange, initializing Diffie-Hellman")
        self.dh = DiffieHellman(group=14)

    @Pyro4.expose
    def exchange_key(self, other_public_key):
        print("received a public key, calculating shared secret...")
        self.dh.make_shared_secret_and_key(other_public_key)
        print("shared secret key = ", self.dh.key)
        return self.dh.public_key


Pyro5.api.Daemon.serveSimple({
    KeyExchange: "example.dh.keyexchange"
}, ns=True)
