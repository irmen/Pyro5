import serpent
from Pyro5.api import expose, serve, config
import Pyro5.socketutil


class Testclass(object):
    @expose
    def transfer(self, data):
        if config.SERIALIZER == "serpent" and type(data) is dict:
            data = serpent.tobytes(data)  # in case of serpent encoded bytes
        print("received %d bytes" % len(data))
        return len(data)

    @expose
    def download_chunks(self, size):
        print("client requests a 'streaming' download of %d bytes" % size)
        data = bytearray(size)
        i = 0
        chunksize = 200000
        print("  using chunks of size", chunksize)
        while i < size:
            yield data[i:i+chunksize]
            i += chunksize


serve(
    {
        Testclass: "example.hugetransfer"
    },
    host=Pyro5.socketutil.get_ip_address("localhost", workaround127=True),
    use_ns=False, verbose=True)
