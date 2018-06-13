from Pyro5.compatibility import Pyro4
import Pyro4


uri = input("enter the server uri: ").strip()
if "\\x00" in uri:
    uri=uri.replace("\\x00", "\x00")
    print("(uri contains 0-byte)")

with Pyro4.Proxy(uri) as p:
    response = p.message("Hello there!")
    print("Response was:", response)
