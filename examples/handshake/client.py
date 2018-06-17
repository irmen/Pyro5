from Pyro5.api import Proxy


class CustomHandshakeProxy(Proxy):
    def _pyroValidateHandshake(self, response):
        # this will get called if the connection is okay by the server
        print("Proxy received handshake response data: ", response)


uri = input("Enter the URI of the server object: ")
secret = input("Enter the secret code of the server (or make a mistake on purpose to see what happens): ")

with CustomHandshakeProxy(uri) as proxy:
    proxy._pyroHandshake = secret
    print("connecting...")
    proxy._pyroBind()
    proxy.ping()
    print("Connection ok!")

print("done.")
