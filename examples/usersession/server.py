from Pyro5.api import behavior, expose, current_context, serve, config
from database import DummyDatabase


config.SERVERTYPE = "thread"
database = DummyDatabase()


@behavior(instance_mode="single")
@expose
class SingletonDatabase(object):
    """
    This pyro object will exhibit problems when used from multiple proxies at the same time
    because it will access the database connection concurrently from different threads
    """
    def __init__(self):
        """
        Initialize the database

        Args:
            self: (todo): write your description
        """
        print("[%s] new instance and connection" % self.__class__.__name__)
        self.conn = database.connect(user=None)  # user is per-call, not global

    def store(self, key, value):
        """
        Stores the given key.

        Args:
            self: (todo): write your description
            key: (str): write your description
            value: (str): write your description
        """
        # get the user-token from the USER annotation
        user_annotation = current_context.annotations["USER"]
        # because we will be storing it for a longer time, make an explicit textual copy of it
        user = bytes(user_annotation).decode("utf-8")
        self.conn.store(key, value, user=user)

    def retrieve(self, key):
        """
        Retrieves an annotation.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        # get the user-token from the USER annotation
        user_annotation = current_context.annotations["USER"]
        return self.conn.retrieve(key, user=bytes(user_annotation).decode("utf-8"))

    def ping(self):
        """
        Returns the ping object.

        Args:
            self: (todo): write your description
        """
        return "hi"


@behavior(instance_mode="session")
@expose
class SessionboundDatabase(object):
    """
    This pyro object will work fine when used from multiple proxies at the same time
    because you'll get a new instance for every new session (proxy connection)
    """
    def __init__(self):
        """
        Initialize the annotation.

        Args:
            self: (todo): write your description
        """
        # get the user-token from the USER annotation
        user_annotation = current_context.annotations["USER"]
        user = bytes(user_annotation).decode("utf-8")
        self.connection = database.connect(user)
        print("[%s] new instance and connection for user: %s" % (self.__class__.__name__, user))

    def store(self, key, value):
        """
        Stores a key in the cache.

        Args:
            self: (todo): write your description
            key: (str): write your description
            value: (str): write your description
        """
        self.connection.store(key, value)

    def retrieve(self, key):
        """
        Retrieves a value from the cache.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        return self.connection.retrieve(key)

    def ping(self):
        """
        Returns the ping object.

        Args:
            self: (todo): write your description
        """
        return "hi"


serve({
    SingletonDatabase: "example.usersession.singletondb",
    SessionboundDatabase: "example.usersession.sessiondb"
})
