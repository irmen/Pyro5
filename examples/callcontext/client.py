import Pyro5.api
import uuid


# example: set a single correlation id on the context that should be passed along
Pyro5.api.current_context.correlation_id = uuid.uuid4()
print("correlation id set to:", Pyro5.api.current_context.correlation_id)


uri = input("Enter the URI of the server object: ")

print("\n------- get annotations via normal proxy and the call context... -----\n")

with Pyro5.api.Proxy(uri) as proxy:
    print("normal call")

    Pyro5.api.current_context.annotations = {"XYZZ": b"custom annotation from client (1)"}
    result = proxy.echo("hi there - new method of annotation access in client")
    print("Annotations in response were: ")
    for key, value in Pyro5.api.current_context.response_annotations.items():
        print("  ", key, "->", bytes(value))

    print("\noneway call")
    Pyro5.api.current_context.annotations = {"XYZZ": b"custom annotation from client (2)"}
    proxy.oneway("hi there ONEWAY - new method of annotation access in client")
    print("Annotations in response were: ")
    for key, value in Pyro5.api.current_context.response_annotations.items():
        print("  ", key, "->", bytes(value))
    print("(should be an empty result because oneway!)")


print("\nSee the console output on the server for more results.")
