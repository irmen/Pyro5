# defines custom classes


class Thingy(object):
    def __init__(self, num):
        """
        Initialize num

        Args:
            self: (todo): write your description
            num: (int): write your description
        """
        self.number = num

    def __str__(self):
        """
        Generate a unique hex string.

        Args:
            self: (todo): write your description
        """
        return "<Thingy @" + hex(id(self)) + ", number=" + str(self.number) + ">"


class OtherThingy(object):
    def __init__(self, num):
        """
        Initialize num

        Args:
            self: (todo): write your description
            num: (int): write your description
        """
        self.number = num

    def __str__(self):
        """
        Generate a unique hex string.

        Args:
            self: (todo): write your description
        """
        return "<OtherThingy @" + hex(id(self)) + ", number=" + str(self.number) + ">"
