import Pyro5.api


uri = input("Enter the uri of the restricted server: ")
restricted = Pyro5.api.Proxy(uri)
print("server is running as:", restricted.who_is_server())
print("attempting to write a file:")
try:
    restricted.write_file()
    print("???? this should fail!")
except OSError as x:
    print("ERROR (expected):", x)
