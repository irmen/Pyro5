import threading
import time
import sys
import Pyro5.errors
import Pyro5.api

sys.excepthook = Pyro5.errors.excepthook


def get_user_token():
    return "user123"


class DbAccessor(threading.Thread):
    def __init__(self, uri):
        super(DbAccessor, self).__init__()
        self.uri = uri
        self.daemon = True

    def run(self):
        proxy = Pyro5.api.Proxy(self.uri)
        for i in range(3):
            try:
                Pyro5.api.current_context.annotations = {"USER": get_user_token().encode("utf-8")}
                proxy.store("number", 100+i)
                num = proxy.retrieve("number")
                print("[%s] num=%s" % (self.name, num))
            except Exception:
                import traceback
                traceback.print_exc()


print("\n***** Sequential access using multiple proxies on the Session-Bound Database... (no issues)")

with Pyro5.api.Proxy("PYRONAME:example.usersession.sessiondb") as p1, \
        Pyro5.api.Proxy("PYRONAME:example.usersession.sessiondb") as p2:
    Pyro5.api.current_context.annotations = {"USER": get_user_token().encode("utf-8")}
    p1.store("number", 42)
    p1.retrieve("number")
    p2.store("number", 43)
    p2.retrieve("number")

print("\n***** Sequential access using multiple proxies on the Singleton Database... (no issues)")
with Pyro5.api.Proxy("PYRONAME:example.usersession.singletondb") as p1, \
        Pyro5.api.Proxy("PYRONAME:example.usersession.singletondb") as p2:
    Pyro5.api.current_context.annotations = {"USER": get_user_token().encode("utf-8")}
    p1.store("number", 42)
    p1.retrieve("number")
    p2.store("number", 43)
    p2.retrieve("number")

print("\n***** Multiple concurrent proxies on the Session-Bound Database... (no issues)")
input("enter to start: ")
t1 = DbAccessor("PYRONAME:example.usersession.sessiondb")
t2 = DbAccessor("PYRONAME:example.usersession.sessiondb")
t1.start()
t2.start()
time.sleep(1)
t1.join()
t2.join()

print("\n***** Multiple concurrent proxies on the Singleton Database... (concurrency errors will occur!)")
input("enter to start: ")
t1 = DbAccessor("PYRONAME:example.usersession.singletondb")
t2 = DbAccessor("PYRONAME:example.usersession.singletondb")
t1.start()
t2.start()
time.sleep(1)
t1.join()
t2.join()
