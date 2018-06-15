# Client that doesn't use the Name Server. Uses URI directly.

from Pyro5.compatibility import Pyro4
import Pyro4


uri = input("Enter the URI of the quote object: ")
with Pyro4.Proxy(uri) as quotegen:
    print("Getting some quotes...")
    print(quotegen.quote())
    print(quotegen.quote())
