from Pyro5.api import expose


@expose
class ShoppingCart(object):
    def __init__(self):
        """
        Initialize the contents.

        Args:
            self: (todo): write your description
        """
        self.contents = []
        print("(shoppingcart %d taken)" % id(self))

    def purchase(self, item):
        """
        Add an item to the list.

        Args:
            self: (todo): write your description
            item: (int): write your description
        """
        self.contents.append(item)
        print("(%s put into shoppingcart %d)" % (item, id(self)))

    def empty(self):
        """
        Empty the contents of the contents.

        Args:
            self: (todo): write your description
        """
        self.contents = []

    def getContents(self):
        """
        Get the contents of the file.

        Args:
            self: (todo): write your description
        """
        return self.contents
