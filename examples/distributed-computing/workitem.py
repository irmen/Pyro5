class Workitem(object):
    def __init__(self, itemId, data):
        """
        Initialize item id

        Args:
            self: (todo): write your description
            itemId: (str): write your description
            data: (todo): write your description
        """
        print("Created workitem %s" % itemId)
        self.itemId = itemId
        self.data = data
        self.result = None
        self.processedBy = None

    def __str__(self):
        """
        Returns the string representation of this item.

        Args:
            self: (todo): write your description
        """
        return "<Workitem id=%s>" % str(self.itemId)

    @staticmethod
    def from_dict(classname, d):
        """this method is used to deserialize a workitem from Pyro"""
        assert classname == "workitem.Workitem"
        w = Workitem(d["itemId"], d["data"])
        w.result = d["result"]
        w.processedBy = d["processedBy"]
        return w
