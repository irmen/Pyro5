from Pyro5.api import expose, behavior, serve


@expose
@behavior(instance_mode="single")
class Warehouse(object):
    def __init__(self):
        """
        Initialize the content

        Args:
            self: (todo): write your description
        """
        self.contents = ["chair", "bike", "flashlight", "laptop", "couch"]

    def list_contents(self):
        """
        Returns the contents of the contents.

        Args:
            self: (todo): write your description
        """
        return self.contents

    def take(self, name, item):
        """
        Removes an item from the list.

        Args:
            self: (todo): write your description
            name: (str): write your description
            item: (todo): write your description
        """
        self.contents.remove(item)
        print("{0} took the {1}.".format(name, item))

    def store(self, name, item):
        """
        Store item in - memory.

        Args:
            self: (todo): write your description
            name: (str): write your description
            item: (todo): write your description
        """
        self.contents.append(item)
        print("{0} stored the {1}.".format(name, item))


serve(
    {
        Warehouse: "example.warehouse"
    },
    use_ns=True)
