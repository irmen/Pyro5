This example shows how you can customize the connection handshake mechanism.

The proxy is overridden to send custom handshake data to the daemon, in this case,
a "secret" string to gain access.

The daemon is overridden to check the handshake string and only allow a client
connection if it sends the correct "secret" string.
