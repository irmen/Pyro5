
def pyro_class_serpent_serializer(obj, serializer, stream, level):
    # Override the default way that a Pyro URI/proxy/daemon is serialized.
    # Because it defines a __getstate__ it would otherwise just become a tuple,
    # and not be deserialized as a class.
    d = SerializerBase.class_to_dict(obj)
    serializer.ser_builtins_dict(d, stream, level)


def serialize_pyro_object_to_dict(obj):
    return {
        "__class__": "{:s}.{:s}".format(obj.__module__, + obj.__class__.__name__),
        "state": obj.__getstate_for_dict__()
    }


def get_serializer_by_id(serializer_id):
    raise NotImplementedError


def get_serializer(name):
    raise NotImplementedError


class SerializerBase:
    @classmethod
    def class_to_dict(cls, object):
        pass  # XXX
    @classmethod
    def register_class_to_dict(cls, clazz, method, serpent_too=False):
        pass  # XXX


class MarshalSerializer(SerializerBase):
    pass
