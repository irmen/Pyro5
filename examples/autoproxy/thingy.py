from Pyro5.api import expose


@expose
class Thingy(object):
    def __init__(self, number):
        """
        Initialize a number.

        Args:
            self: (todo): write your description
            number: (int): write your description
        """
        self.number = number

    def speak(self, message):
        """
        Prints a message

        Args:
            self: (todo): write your description
            message: (str): write your description
        """
        print("Thingy {0} says: {1}".format(self.number, message))
