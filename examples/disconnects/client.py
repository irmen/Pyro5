import warnings
import Pyro5.api
import Pyro5.protocol
import Pyro5.errors


warnings.filterwarnings("ignore")

print("You can run this client on a different computer so you can disable the network connection (by yanking out the lan cable or whatever).")
print("Alternatively, wait for a timeout on the server, which will then close its connection.")
uri = input("Uri of server? ").strip()


class AutoReconnectingProxy(Pyro5.api.Proxy):
    """
    A Pyro proxy that automatically recovers from a server disconnect.
    It does this by intercepting every method call and then it first 'pings'
    the server to see if it still has a working connection. If not, it
    reconnects the proxy and retries the method call.
    Drawback is that every method call now uses two remote messages (a ping,
    and the actual method call).
    This uses some advanced features of the Pyro API.
    """

    def _pyroInvoke(self, *args, **kwargs):
        """
        Called bytest5 client.

        Args:
            self: (todo): write your description
        """
        # We override the method that does the actual remote calls: _pyroInvoke.
        # If there's still a connection, try a ping to see if it is still alive.
        # If it isn't alive, reconnect it. If there's no connection, simply call
        # the original method (it will reconnect automatically).
        if self._pyroConnection:
            try:
                print("  <proxy: ping>")
                Pyro5.protocol.SendingMessage.ping(self._pyroConnection)    # utility method on the Message class
                print("  <proxy: ping reply (still connected)>")
            except Pyro5.errors.ConnectionClosedError:
                print("  <proxy: Connection lost. REBINDING...>")
                self._pyroReconnect()
                print("  <proxy: Connection restored, continue with actual method call...>")
        return super(AutoReconnectingProxy, self)._pyroInvoke(*args, **kwargs)


with AutoReconnectingProxy(uri) as obj:
    result = obj.echo("12345")
    print("result =", result)
    print("\nClient proxy connection is still open. Disable the network now (or wait until the connection timeout on the server expires) and see what the server does.")
    print("Once you see on the server that it got a timeout or a disconnect, enable the network again.")
    input("Press enter to continue:")
    print("\nDoing a new call on the same proxy:")
    result = obj.echo("12345")
    print("result =", result)
