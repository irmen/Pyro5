import sys
import Pyro5.errors
import Pyro5.api


sys.excepthook = Pyro5.errors.excepthook


uri = input("Enter streaming server uri: ").strip()
with Pyro5.api.Proxy(uri) as p:
    print("\nnormal list:")
    print(p.list())
    print("\nvia iterator:")
    print(list(p.iterator()))
    print("\nvia generator:")
    print(list(p.generator()))
    print("\nslow generator:")
    for number in p.slow_generator():
        print(number)
