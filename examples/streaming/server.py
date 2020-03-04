import time
from Pyro5.api import expose, serve, config


if config.ITER_STREAMING:
    print("Note: iter-streaming has been enabled in the Pyro config.")
else:
    print("Note: iter-streaming has not been enabled in the Pyro config (PYRO_ITER_STREAMING).")


@expose
class Streamer(object):
    def list(self):
        return [1, 2, 3, 4, 5, 6, 7, 8, 9]

    def iterator(self):
        return iter([1, 2, 3, 4, 5, 6, 7, 8, 9])

    def generator(self):
        i = 1
        while i < 10:
            yield i
            i += 1

    def slow_generator(self):
        i = 1
        while i < 10:
            time.sleep(0.5)
            yield i
            i += 1

    def fibonacci(self):
        a, b = 0, 1
        while True:
            yield a
            a, b = b, a + b


serve({
        Streamer: "example.streamer"
    }, use_ns=False)
