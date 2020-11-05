import time
from Pyro5.api import expose, serve, config


if config.ITER_STREAMING:
    print("Note: iter-streaming has been enabled in the Pyro config.")
else:
    print("Note: iter-streaming has not been enabled in the Pyro config (PYRO_ITER_STREAMING).")


@expose
class Streamer(object):
    def list(self):
        """
        !

        Args:
            self: (todo): write your description
        """
        return [1, 2, 3, 4, 5, 6, 7, 8, 9]

    def iterator(self):
        """
        Return an iterator that iterating over an iterator.

        Args:
            self: (todo): write your description
        """
        return iter([1, 2, 3, 4, 5, 6, 7, 8, 9])

    def generator(self):
        """
        Generate an iterator that yields a generator.

        Args:
            self: (todo): write your description
        """
        i = 1
        while i < 10:
            yield i
            i += 1

    def slow_generator(self):
        """
        A generator that yields a generator that yields a generator.

        Args:
            self: (todo): write your description
        """
        i = 1
        while i < 10:
            time.sleep(0.5)
            yield i
            i += 1

    def fibonacci(self):
        """
        Fibonacci version of : class : param b.

        Args:
            self: (todo): write your description
        """
        a, b = 0, 1
        while True:
            yield a
            a, b = b, a + b


serve({
        Streamer: "example.streamer"
    }, use_ns=False)
