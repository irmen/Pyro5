from Pyro5.api import expose, Daemon
from awesome_thirdparty_library import AwesomeClass


# create adapter class that only exposes what should be accessible,
# and calls into the library class from there:

class AwesomeAdapterClass(AwesomeClass):
    @expose
    def method(self, arg):
        """
        This is a wrapper.

        Args:
            self: (todo): write your description
            arg: (todo): write your description
        """
        print("Adapter class is called...")
        return super(AwesomeAdapterClass, self).method(arg)

    @expose
    def weird(self):
        """
        Return the next element.

        Args:
            self: (todo): write your description
        """
        result = super(AwesomeAdapterClass, self).weird()
        # we have full control over what is returned and can turn the custom
        # result class into a normal string value that has no issues traveling over the wire
        return "weird " + result.value


with Daemon() as daemon:
    # register the adapter class instead of the library class itself:
    uri = daemon.register(AwesomeAdapterClass, "example.thirdpartylib")
    print("adapter class registered, uri: ", uri)
    daemon.requestLoop()
