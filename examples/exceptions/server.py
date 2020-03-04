from Pyro5.api import Daemon, serve
import excep


def my_error_handler(daemon, client_sock, method, vargs, kwargs, exception):
    print("\nERROR IN METHOD CALL USER CODE:")
    print(" client={} method={} exception={}".format(client_sock, method.__qualname__, repr(exception)))


daemon = Daemon()
daemon.methodcall_error_handler = my_error_handler

serve(
    {
        excep.TestClass: "example.exceptions"
    },
    daemon=daemon,
    use_ns=True, verbose=True)
