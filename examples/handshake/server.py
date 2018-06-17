from Pyro5.api import Daemon
import Pyro5.core


secret_code = "pancakes"


class CustomDaemon(Daemon):
    def validateHandshake(self, conn, data):
        print("Daemon received handshake request from:", conn.sock.getpeername())
        print("Handshake data:", data)
        # if needed, you can inspect Pyro5.core.current_context
        if data == secret_code:
            print("Secret code okay! Connection accepted.")
            # return some custom handshake data:
            return ["how", "are", "you", "doing"]
        else:
            print("Secret code wrong! Connection refused.")
            raise ValueError("wrong secret code, connection refused")

    def clientDisconnect(self, conn):
        print("Daemon client disconnects:", conn.sock.getpeername())


with CustomDaemon() as daemon:
    print("Server is ready. You can use the following URI to connect:")
    print(daemon.uriFor(Pyro5.core.DAEMON_NAME))
    print("When asked, enter the following secret code: ", secret_code)
    daemon.requestLoop()
