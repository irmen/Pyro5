# Client that doesn't use the Name Server. Uses URI directly.

import Pyro4


uri = input("Enter the URI of the quote object: ")
with Pyro4.core.Proxy(uri) as quotegen:
    print("Getting some quotes...")
    print(quotegen.quote())
    print(quotegen.quote())
