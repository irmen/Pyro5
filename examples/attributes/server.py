from Pyro5.api import expose, serve


something = "Something"


@expose
class Thingy(object):
    def __init__(self):
        """
        Initialize the game.

        Args:
            self: (todo): write your description
        """
        self.sub = {"name": "value"}
        self.value = 42
        self._value = 123
        self.__value = 999

    def __dunder__(self):
        """
        Return a copy of a copy.

        Args:
            self: (todo): write your description
        """
        return "yep"

    def __len__(self):
        """
        Returns the number of bytes.

        Args:
            self: (todo): write your description
        """
        return 200

    def getValue(self):
        """
        Returns the value of this field.

        Args:
            self: (todo): write your description
        """
        return self.value

    @property
    def prop_value(self):
        """
        Return the value of the property

        Args:
            self: (todo): write your description
        """
        return self.value

    @prop_value.setter
    def prop_value(self, value):
        """
        Set the value of the property.

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        self.value = value

    @property
    def prop_sub(self):
        """
        Propagate sub - sub - sub - sub - sub - sub - sub - sub - sub - sub - sub - class

        Args:
            self: (todo): write your description
        """
        return self.sub


serve({
    Thingy: "example.attributes"
}, use_ns=False)
