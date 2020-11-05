from Pyro5.api import expose, Proxy, register_dict_to_class
from customdata import CustomData

# teach the serializer how to deserialize our custom data class
register_dict_to_class(CustomData.serialized_classname, CustomData.from_dict)


class Listener(object):
    def __init__(self, topic):
        """
        Initialize the given topic.

        Args:
            self: (todo): write your description
            topic: (int): write your description
        """
        self.topic = topic

    def register_with_dispatcher(self):
        """
        Register a callback to the channel.

        Args:
            self: (todo): write your description
        """
        with Proxy("PYRONAME:example.blobdispatcher") as dispatcher:
            dispatcher.register(self.topic, self)

    @expose
    def process_blob(self, blob):
        """
        Process blob

        Args:
            self: (todo): write your description
            blob: (todo): write your description
        """
        assert blob.info == self.topic
        customdata = blob.deserialized()
        print("Received custom data (type={}):".format(type(customdata)))
        print("    a={}, b={}, c={}".format(customdata.a, customdata.b, customdata.c))
