from Pyro5.api import Daemon
import excep


def my_error_handler(daemon, client_sock, method, vargs, kwargs, exception):
    print("\nERROR IN METHOD CALL USER CODE:")
    print(" client={} method={} exception={}".format(client_sock, method.__qualname__, repr(exception)))


daemon = Daemon()
daemon.methodcall_error_handler = my_error_handler

Daemon.serveSimple(
    {
        excep.TestClass: "example.exceptions"
    },
    daemon=daemon,
    ns=True, verbose=True)
