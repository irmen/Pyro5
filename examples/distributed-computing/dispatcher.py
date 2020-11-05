import queue
from Pyro5.api import expose, behavior, serve, register_dict_to_class
from workitem import Workitem


# For 'workitem.Workitem' we register a deserialization hook to be able to get these back from Pyro
register_dict_to_class("workitem.Workitem", Workitem.from_dict)


@expose
@behavior(instance_mode="single")
class DispatcherQueue(object):
    def __init__(self):
        """
        Initialize the queue.

        Args:
            self: (todo): write your description
        """
        self.workqueue = queue.Queue()
        self.resultqueue = queue.Queue()

    def putWork(self, item):
        """
        Put the given item into the queue.

        Args:
            self: (todo): write your description
            item: (array): write your description
        """
        self.workqueue.put(item)

    def getWork(self, timeout=5):
        """
        Get a list of the work queue.

        Args:
            self: (todo): write your description
            timeout: (int): write your description
        """
        try:
            return self.workqueue.get(block=True, timeout=timeout)
        except queue.Empty:
            raise ValueError("no items in queue")

    def putResult(self, item):
        """
        Put an item into the queue.

        Args:
            self: (todo): write your description
            item: (todo): write your description
        """
        self.resultqueue.put(item)

    def getResult(self, timeout=5):
        """
        Get the next result from the queue.

        Args:
            self: (todo): write your description
            timeout: (int): write your description
        """
        try:
            return self.resultqueue.get(block=True, timeout=timeout)
        except queue.Empty:
            raise ValueError("no result available")

    def workQueueSize(self):
        """
        Returns the total number of the queue.

        Args:
            self: (todo): write your description
        """
        return self.workqueue.qsize()

    def resultQueueSize(self):
        """
        The total number of the queue.

        Args:
            self: (todo): write your description
        """
        return self.resultqueue.qsize()


# main program

serve({
    DispatcherQueue: "example.distributed.dispatcher"
})
