import time
import warnings
import serpent
from Pyro5.api import Proxy, config


warnings.filterwarnings("ignore")

print("Enter the server's uri that was printed:")
uri = input().strip()

datasize = 5 * 1024 * 1024  # 5 mb


def do_test(data):
    """
    Test for the test.

    Args:
        data: (array): write your description
    """
    assert len(data) == datasize
    totalsize = 0

    with Proxy(uri) as obj:
        obj._pyroBind()

        begin = time.time()
        for i in range(10):
            print("transferring %d bytes" % datasize)
            size = obj.transfer(data)
            assert size == datasize
            totalsize += datasize
        duration = time.time() - begin

        totalsize = float(totalsize)
        print("It took %.2f seconds to transfer %d mb." % (duration, totalsize / 1024 / 1024))
        print("That is %.0f kb/sec. = %.1f mb/sec. (serializer: %s)" %
              (totalsize / 1024 / duration, totalsize / 1024 / 1024 / duration, config.SERIALIZER))


def do_test_chunks():
    """
    Do a chunk of chunks.

    Args:
    """
    with Proxy(uri) as p:
        totalsize = 0
        begin = time.time()
        for chunk in p.download_chunks(datasize*10):
            chunk = serpent.tobytes(chunk)  # in case of serpent encoded bytes
            totalsize += len(chunk)
            print(".", end="", flush=True)
        assert totalsize == datasize*10
        duration = time.time() - begin
        totalsize = float(totalsize)
        print("\nIt took %.2f seconds to transfer %d mb." % (duration, totalsize / 1024 / 1024))
        print("That is %.0f kb/sec. = %.1f mb/sec. (serializer: %s)" %
              (totalsize / 1024 / duration, totalsize / 1024 / 1024 / duration, config.SERIALIZER))


data = 'x' * datasize
print("\n\n----test with string data----")
do_test(data)
print("\n\n----test with byte data----")
data = b'x' * datasize
do_test(data)
data = bytearray(b'x' * datasize)
print("\n\n----test with bytearray data----")
do_test(data)
print("\n\n----test download via iterator----")
do_test_chunks()
print("\n\n (tip: also see the 'filetransfer' example for more efficient ways to transfer large amoungs of binary data)")
