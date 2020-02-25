import Pyro5.api


uri = input("Enter the uri of the dmesg server: ")
dmesg = Pyro5.api.Proxy(uri)
try:
    print("Last few lines of the dmesg kernel buffer:\n")
    lines = dmesg.dmesg()
    print("\n".join(lines))
    print("\nNormally you can't read this info from a non-root user. "
          "But the server is running as root and is able to access it for you.")
    print("TIP: now kill the server if you no longer need it!")
except Exception as x:
    print("ERROR:", x)
    print("Is the server running with root privileges?")
