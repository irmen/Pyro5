class Person(object):
    def __init__(self, name):
        """
        Sets the name.

        Args:
            self: (todo): write your description
            name: (str): write your description
        """
        self.name = name

    def visit(self, warehouse):
        """
        Called bytestring

        Args:
            self: (todo): write your description
            warehouse: (bool): write your description
        """
        print("This is {0}.".format(self.name))
        self.deposit(warehouse)
        self.retrieve(warehouse)
        print("Thank you, come again!")

    def deposit(self, warehouse):
        """
        Deprecated.

        Args:
            self: (todo): write your description
            warehouse: (todo): write your description
        """
        print("The warehouse contains:", warehouse.list_contents())
        item = input("Type a thing you want to store (or empty): ").strip()
        if item:
            warehouse.store(self.name, item)

    def retrieve(self, warehouse):
        """
        Retrieve a list of existing devices.

        Args:
            self: (todo): write your description
            warehouse: (todo): write your description
        """
        print("The warehouse contains:", warehouse.list_contents())
        item = input("Type something you want to take (or empty): ").strip()
        if item:
            warehouse.take(self.name, item)
