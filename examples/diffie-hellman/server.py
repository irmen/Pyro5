from Pyro5.api import behavior, expose, locate_ns, serve, config
from diffiehellman import DiffieHellman


config.SERVERTYPE = "multiplex"

ns = locate_ns()


@behavior(instance_mode="session")
class KeyExchange(object):
    def __init__(self):
        """
        Initialize groups

        Args:
            self: (todo): write your description
        """
        print("New KeyExchange, initializing Diffie-Hellman")
        self.dh = DiffieHellman(group=14)

    @expose
    def exchange_key(self, other_public_key):
        """
        Exchange the public key of this key is not be used to change the public key.

        Args:
            self: (todo): write your description
            other_public_key: (str): write your description
        """
        print("received a public key, calculating shared secret...")
        self.dh.make_shared_secret_and_key(other_public_key)
        print("shared secret key = ", self.dh.key.hex())
        return self.dh.public_key


serve({
    KeyExchange: "example.dh.keyexchange"
}, use_ns=True)
