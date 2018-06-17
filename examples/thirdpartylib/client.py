from Pyro5.api import Proxy
import Pyro5.errors


uri = input("Enter the URI of the thirdparty library object: ").strip()
with Proxy(uri) as remote:
    print(remote.method("how are you?"))

    try:
        print(remote.weird())
    except Pyro5.errors.SerializeError:
        print("couldn't call weird() due to serialization error of the result value! (is ok)")

    try:
        print(remote.private())    # we can call this if full class is exposed...
    except AttributeError:
        print("couldn't call private(), it doesn't seem to be exposed! (is ok)")
