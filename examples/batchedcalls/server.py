import time
from Pyro5.api import expose, serve


@expose
class Thingy(object):
    def multiply(self, a, b):
        """
        Multiply two lists.

        Args:
            self: (todo): write your description
            a: (array): write your description
            b: (array): write your description
        """
        return a * b

    def add(self, a, b):
        """
        Add two arguments.

        Args:
            self: (todo): write your description
            a: (int): write your description
            b: (int): write your description
        """
        return a + b

    def divide(self, a, b):
        """
        Divide two numbers.

        Args:
            self: (todo): write your description
            a: (int): write your description
            b: (int): write your description
        """
        return a // b

    def error(self):
        """
        Return the error.

        Args:
            self: (todo): write your description
        """
        return 1 // 0

    def delay(self, seconds):
        """
        Return the number of seconds.

        Args:
            self: (todo): write your description
            seconds: (float): write your description
        """
        time.sleep(seconds)
        return seconds

    def printmessage(self, message):
        """
        Print a message

        Args:
            self: (todo): write your description
            message: (str): write your description
        """
        print(message)
        return 0


serve({
    Thingy: "example.batched"
}, use_ns=False)
