Diffie-Hellman key exchange.

Sometimes the server and client have to use the same symmetric private key, for instance
to do symmetric data encryption.
It can be problematic to distribute such a shared private key among your client and server code,
as you may not want to hardcode it (especially in the client!)

There's are secure algorithms to tackle the "key exchange" problem, and this example shows
one of them: the Diffie-Hellman key exchange. It's based on calculating stuff with large prime
exponenents and modulos, but in the end, both the client and server agree on a shared secret key
that: a) has never publicly been sent over the wire, b) is not hardcoded anywhere.


IMPORTANT NOTE:

In this particular example there is NO ENCRYPTION done whatsoever. Encryption is a different topic!
If you want, you can enable SSL/TLS in Pyro as well to provide this. However, if you use 2-way-ssl,
this makes the use of a shared private key somewhat obsolete, because mutual verification of the SSL certificates
essentially does the same thing. See the SSL example for more details.
