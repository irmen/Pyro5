import Pyro5.errors
import Pyro5.api


class Safe(object):
    @Pyro5.api.expose
    def echo(self, message):
        print("got message:", message)
        return "hi!"


Pyro5.config.SSL = True
Pyro5.config.SSL_REQUIRECLIENTCERT = True   # enable 2-way ssl
Pyro5.config.SSL_SERVERCERT = "../../certs/server_cert.pem"
Pyro5.config.SSL_SERVERKEY = "../../certs/server_key.pem"
Pyro5.config.SSL_CACERTS = "../../certs/client_cert.pem"    # to make ssl accept the self-signed client cert
print("SSL enabled (2-way).")


class CertValidatingDaemon(Pyro5.api.Daemon):
    def validateHandshake(self, conn, data):
        cert = conn.getpeercert()
        if not cert:
            raise Pyro5.errors.CommunicationError("client cert missing")
        # note: hostname and expiry date validation is already successfully performed by the SSL layer itself
        # not_before = datetime.datetime.utcfromtimestamp(ssl.cert_time_to_seconds(cert["notBefore"]))
        # print("not before:", not_before)
        # not_after = datetime.datetime.utcfromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]))
        # print("not after:", not_after)
        # today = datetime.datetime.now()
        # if today > not_after or today < not_before:
        #     raise Pyro5.errors.CommunicationError("cert not yet valid or expired")
        if cert["serialNumber"] != "DC3EFDB52BE9D350":
            raise Pyro5.errors.CommunicationError("cert serial number incorrect", cert["serialNumber"])
        issuer = dict(p[0] for p in cert["issuer"])
        subject = dict(p[0] for p in cert["subject"])
        if issuer["organizationName"] != "Razorvine.net":
            # issuer is not often relevant I guess, but just to show that you have the data
            raise Pyro5.errors.CommunicationError("cert not issued by Razorvine.net")
        if subject["countryName"] != "NL":
            raise Pyro5.errors.CommunicationError("cert not for country NL")
        if subject["organizationName"] != "Razorvine.net":
            raise Pyro5.errors.CommunicationError("cert not for Razorvine.net")
        print("(SSL client cert is ok: serial={ser}, subject={subj})"
              .format(ser=cert["serialNumber"], subj=subject["organizationName"]))
        return super(CertValidatingDaemon, self).validateHandshake(conn, data)


d = CertValidatingDaemon()
uri = d.register(Safe)
print("server uri:", uri)
d.requestLoop()
