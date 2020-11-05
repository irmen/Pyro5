from Pyro5.api import expose, Proxy


# a Chain member. Passes messages to the next link,
# until the message went full-circle: then it exits.

class Chain(object):
    def __init__(self, name, next_node):
        """
        Create a new node.

        Args:
            self: (todo): write your description
            name: (str): write your description
            next_node: (str): write your description
        """
        self.name = name
        self.nextName = next_node
        self.next = None

    @expose
    def process(self, message):
        """
        Process the next message

        Args:
            self: (todo): write your description
            message: (str): write your description
        """
        if self.next is None:
            self.next = Proxy("PYRONAME:example.chain." + self.nextName)
        if self.name in message:
            print("Back at %s; we completed the circle!" % self.name)
            return ["complete at " + self.name]
        else:
            print("I'm %s, passing to %s" % (self.name, self.nextName))
            message.append(self.name)
            result = self.next.process(message)
            result.insert(0, "passed on from " + self.name)
            return result
