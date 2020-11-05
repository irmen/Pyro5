from Pyro5.api import Proxy, config, register_dict_to_class, register_class_to_dict
import mycustomclasses


# use serpent
config.SERIALIZER = "serpent"


# register the special serialization hooks

def thingy_class_to_dict(obj):
    """
    Convert an object as a dict.

    Args:
        obj: (todo): write your description
    """
    print("{serializer hook, converting to dict: %s}" % obj)
    return {
        "__class__": "waheeee-custom-thingy",
        "number-attribute": obj.number
    }


def thingy_dict_to_class(classname, d):
    """
    Convert a dictionary to a dictionary.

    Args:
        classname: (str): write your description
        d: (todo): write your description
    """
    print("{deserializer hook, converting to class: %s}" % d)
    return mycustomclasses.Thingy(d["number-attribute"])


def otherthingy_dict_to_class(classname, d):
    """
    Convert a dictionary of classes to a class.

    Args:
        classname: (str): write your description
        d: (todo): write your description
    """
    print("{deserializer hook, converting to class: %s}" % d)
    return mycustomclasses.OtherThingy(d["number"])


# for 'Thingy' we register both serialization and deserialization hooks
register_class_to_dict(mycustomclasses.Thingy, thingy_class_to_dict)
register_dict_to_class("waheeee-custom-thingy", thingy_dict_to_class)

# for 'OtherThingy' we only register a deserialization hook (and for serialization depend on serpent's default behavior)
register_dict_to_class("mycustomclasses.OtherThingy", otherthingy_dict_to_class)


# regular pyro stuff
uri = input("Enter the URI of the server object: ")
serv = Proxy(uri)
print("\nTransferring thingy...")
o = mycustomclasses.Thingy(42)
response = serv.method(o)
print("type of response object:", type(response))
print("response:", response)
print("\nTransferring otherthingy...")
o = mycustomclasses.OtherThingy(42)
response = serv.othermethod(o)
print("type of response object:", type(response))
print("response:", response)
