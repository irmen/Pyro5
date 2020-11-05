# This is an AWESOME LIBRARY.
# You can use its AWESOME CLASSES to do Great Things.
# The author however DOESN'T allow you to CHANGE the source code and taint it with Pyro decorators!


class WeirdReturnType(object):
    def __init__(self, value):
        """
        Initialize the value

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        self.value = value


class AwesomeClass(object):
    def method(self, arg):
        """
        Prints the argument

        Args:
            self: (todo): write your description
            arg: (todo): write your description
        """
        print("Awesome object is called with: ", arg)
        return "awesome"

    def private(self):
        """
        The private private key

        Args:
            self: (todo): write your description
        """
        print("This should be a private method...")
        return "boo"

    def weird(self):
        """
        Returns a list of the - tick

        Args:
            self: (todo): write your description
        """
        print("Weird!")
        return WeirdReturnType("awesome")
