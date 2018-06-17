import time
from Pyro5.api import Proxy


print("First make sure one of the gui servers is running.")
print("Enter the object uri that was printed:")
uri = input().strip()
guiserver = Proxy(uri)

guiserver.message("Hello there!")
time.sleep(0.5)
guiserver.message("How's it going?")
time.sleep(2)

for i in range(20):
    guiserver.message("Counting {0}".format(i))

guiserver.message("now calling the sleep method with 5 seconds")
guiserver.sleep(5)
print("done!")
