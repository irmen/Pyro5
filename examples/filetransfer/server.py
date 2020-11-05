import select
import tempfile
import uuid
import io
import os
import threading
import zlib
from Pyro5.api import expose, current_context, Daemon, config
import Pyro5.socketutil


datafiles = {}      # temporary files
datablobs = {}      # in-memory


@expose
class FileServer(object):
    def get_with_pyro(self, size):
        """
        Gets pyroro.

        Args:
            self: (todo): write your description
            size: (int): write your description
        """
        print("sending %d bytes" % size)
        data = b"x" * size
        return data

    def iterator(self, size):
        """
        Iterator that yields chunks from the given size.

        Args:
            self: (todo): write your description
            size: (int): write your description
        """
        chunksize = size//100
        print("sending %d bytes via iterator, chunks of %d bytes" % (size, chunksize))
        data = b"x" * size
        i = 0
        while i < size:
            yield data[i:i+chunksize]
            i += chunksize

    def annotation_stream(self, with_checksum=False):
        """
        Yields a generator of the given annotation.

        Args:
            self: (todo): write your description
            with_checksum: (bool): write your description
        """
        # create a large temporary file
        f = tempfile.TemporaryFile()
        for _ in range(5000):
            f.write(b"1234567890!" * 1000)
        filesize = f.tell()
        f.seek(os.SEEK_SET, 0)
        # return the file data via annotation stream (remote iterator)
        annotation_size = 500000
        print("transmitting file via annotations stream (%d bytes in chunks of %d)..." % (filesize, annotation_size))
        with f:
            while True:
                chunk = f.read(annotation_size)
                if not chunk:
                    break
                # store the file data chunk in the FDAT response annotation,
                # and return the current file position and checksum (if asked).
                current_context.response_annotations = {"FDAT": chunk}
                yield f.tell(), zlib.crc32(chunk) if with_checksum else 0

    def prepare_file_blob(self, size):
        """
        Prepare blobs for blobs

        Args:
            self: (todo): write your description
            size: (int): write your description
        """
        print("preparing file-based blob of size %d" % size)
        file_id = str(uuid.uuid4())
        f = tempfile.TemporaryFile()
        chunk = b"x" * 100000
        for _ in range(size//100000):
            f.write(chunk)
        f.write(b"x"*(size % 100000))
        f.flush()
        f.seek(0, io.SEEK_SET)
        # os.fsync(f)
        datafiles[file_id] = f
        blobsock_info = self._pyroDaemon.blobsocket.getsockname()  # return the port info for the blob socket as well
        return file_id, blobsock_info

    def prepare_memory_blob(self, size):
        """
        Prepare blobs for blobs.

        Args:
            self: (todo): write your description
            size: (int): write your description
        """
        print("preparing in-memory blob of size %d" % size)
        file_id = str(uuid.uuid4())
        datablobs[file_id] = b"x" * size
        blobsock_info = self._pyroDaemon.blobsocket.getsockname()  # return the port info for the blob socket as well
        return file_id, blobsock_info


class FileServerDaemon(Daemon):
    def __init__(self, host=None, port=0):
        """
        Initialize blobs

        Args:
            self: (todo): write your description
            host: (str): write your description
            port: (int): write your description
        """
        super(FileServerDaemon, self).__init__(host, port)
        host = self.transportServer.sock.getsockname()[0]
        self.blobsocket = Pyro5.socketutil.create_socket(bind=(host, 0), timeout=config.COMMTIMEOUT, nodelay=False)
        print("Blob socket available on:", self.blobsocket.getsockname())

    def close(self):
        """
        Closes the file.

        Args:
            self: (todo): write your description
        """
        self.blobsocket.close()
        super(FileServerDaemon, self).close()

    def requestLoop(self, loopCondition=lambda: True):
        """
        Starts events.

        Args:
            self: (todo): write your description
            loopCondition: (todo): write your description
        """
        while loopCondition:
            rs = [self.blobsocket]
            rs.extend(self.sockets)
            rs, _, _ = select.select(rs, [], [], 3)
            daemon_events = []
            for sock in rs:
                if sock in self.sockets:
                    daemon_events.append(sock)
                elif sock is self.blobsocket:
                    self.handle_blob_connect(sock)
            if daemon_events:
                self.events(daemon_events)

    def handle_blob_connect(self, sock):
        """
        Handle a blob blob.

        Args:
            self: (todo): write your description
            sock: (todo): write your description
        """
        csock, caddr = sock.accept()
        thread = threading.Thread(target=self.blob_client, args=(csock,))
        thread.daemon = True
        thread.start()

    def blob_client(self, csock):
        """
        Reads the contents of the client.

        Args:
            self: (todo): write your description
            csock: (todo): write your description
        """
        file_id = Pyro5.socketutil.receive_data(csock, 36).decode()
        print("{0} requesting file id {1}".format(csock.getpeername(), file_id))
        is_file, data = self.find_blob_data(file_id)
        if is_file:
            if hasattr(os, "sendfile"):
                print("...from file using sendfile()")
                out_fn = csock.fileno()
                in_fn = data.fileno()
                sent = 1
                offset = 0
                while sent:
                    sent = os.sendfile(out_fn, in_fn, offset, 512000)
                    offset += sent
            else:
                print("...from file using plain old read(); your os doesn't have sendfile()")
                while True:
                    chunk = data.read(512000)
                    if not chunk:
                        break
                    csock.sendall(chunk)
        else:
            print("...from memory")
            csock.sendall(data)
        csock.close()

    def find_blob_data(self, file_id):
        """
        Find blob file with given file_id.

        Args:
            self: (todo): write your description
            file_id: (str): write your description
        """
        if file_id in datablobs:
            return False, datablobs.pop(file_id)
        elif file_id in datafiles:
            return True, datafiles.pop(file_id)
        else:
            raise KeyError("no data for given id")


with FileServerDaemon(host=Pyro5.socketutil.get_ip_address("")) as daemon:
    uri = daemon.register(FileServer, "example.filetransfer")
    print("Filetransfer server URI:", uri)
    daemon.requestLoop()
