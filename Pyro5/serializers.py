
def get_serializer_by_id(serializer_id):
    raise NotImplementedError


def get_serializer(name):
    raise NotImplementedError


class SerializerBase:
    @classmethod
    def class_to_dict(cls, object):
        raise NotImplementedError
