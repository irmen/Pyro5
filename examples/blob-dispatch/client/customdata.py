# note: this module is shared with the listeners so they can understand the data passed in


class CustomData(object):
    serialized_classname = "blobdispatch.CustomData"

    def __init__(self, a, b, c):
        """
        Initialize a b

        Args:
            self: (todo): write your description
            a: (int): write your description
            b: (int): write your description
            c: (int): write your description
        """
        self.a = a
        self.b = b
        self.c = c

    def to_dict(self):
        """for (serpent) serialization"""
        return {
            "__class__": self.serialized_classname,
            "a": self.a,
            "b": self.b,
            "c": self.c
        }

    @classmethod
    def from_dict(cls, classname, d):
        """for (serpent) deserialization"""
        assert classname == cls.serialized_classname
        obj = cls(d["a"], d["b"], d["c"])
        return obj
