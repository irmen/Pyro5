# Client that doesn't use the Name Server. Uses URI directly.

from Pyro5.api import Proxy


uri = input("Enter the URI of the quote object: ")
with Proxy(uri) as quotegen:
    print("Getting some quotes...")
    print(quotegen.quote())
    print(quotegen.quote())
