"""
Server related classes (Daemon etc)

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import logging
import inspect

__all__ = ["is_private_attribute", "get_exposed_members", "reset_exposed_members", "getAttribute",
           "get_exposed_property_value", "set_exposed_property_value"]

log = logging.getLogger("Pyro5.server")


def getAttribute(obj, attr):
    """
    Resolves an attribute name to an object.  Raises
    an AttributeError if any attribute in the chain starts with a '``_``'.
    Doesn't resolve a dotted name, because that is a security vulnerability.
    It treats it as a single attribute name (and the lookup will likely fail).
    """
    if is_private_attribute(attr):
        raise AttributeError("attempt to access private attribute '%s'" % attr)
    else:
        obj = getattr(obj, attr)
    if getattr(obj, "_pyroExposed", False):
        return obj
    raise AttributeError("attempt to access unexposed attribute '%s'" % attr)


__exposed_member_cache = {}


def reset_exposed_members(obj, only_exposed=True, as_lists=False):
    """Delete any cached exposed members forcing recalculation on next request"""
    if not inspect.isclass(obj):
        obj = obj.__class__
    cache_key = (obj, only_exposed, as_lists)
    __exposed_member_cache.pop(cache_key, None)


def get_exposed_members(obj, only_exposed=True, as_lists=False, use_cache=True):
    """
    Return public and exposed members of the given object's class.
    You can also provide a class directly.
    Private members are ignored no matter what (names starting with underscore).
    If only_exposed is True, only members tagged with the @expose decorator are
    returned. If it is False, all public members are returned.
    The return value consists of the exposed methods, exposed attributes, and methods
    tagged as @oneway.
    (All this is used as meta data that Pyro sends to the proxy if it asks for it)
    as_lists is meant for python 2 compatibility.
    """
    if not inspect.isclass(obj):
        obj = obj.__class__

    cache_key = (obj, only_exposed, as_lists)
    if use_cache and cache_key in __exposed_member_cache:
        return __exposed_member_cache[cache_key]

    methods = set()  # all methods
    oneway = set()  # oneway methods
    attrs = set()  # attributes
    for m in dir(obj):      # also lists names inherited from super classes
        if is_private_attribute(m):
            continue
        v = getattr(obj, m)
        if inspect.ismethod(v) or inspect.isfunction(v):
            if getattr(v, "_pyroExposed", not only_exposed):
                methods.add(m)
                # check if the method is marked with the 'oneway' decorator:
                if getattr(v, "_pyroOneway", False):
                    oneway.add(m)
        elif inspect.isdatadescriptor(v):
            func = getattr(v, "fget", None) or getattr(v, "fset", None) or getattr(v, "fdel", None)
            if func is not None and getattr(func, "_pyroExposed", not only_exposed):
                attrs.add(m)
        # Note that we don't expose plain class attributes no matter what.
        # it is a syntax error to add a decorator on them, and it is not possible
        # to give them a _pyroExposed tag either.
        # The way to expose attributes is by using properties for them.
        # This automatically solves the protection/security issue: you have to
        # explicitly decide to make an attribute into a @property (and to @expose it)
        # before it becomes remotely accessible.
    if as_lists:
        methods = list(methods)
        oneway = list(oneway)
        attrs = list(attrs)
    result = {
        "methods": methods,
        "oneway": oneway,
        "attrs": attrs
    }
    __exposed_member_cache[cache_key] = result
    return result


def get_exposed_property_value(obj, propname, only_exposed=True):
    """
    Return the value of an @exposed @property.
    If the requested property is not a @property or not exposed,
    an AttributeError is raised instead.
    """
    v = getattr(obj.__class__, propname)
    if inspect.isdatadescriptor(v):
        if v.fget and getattr(v.fget, "_pyroExposed", not only_exposed):
            return v.fget(obj)
    raise AttributeError("attempt to access unexposed or unknown remote attribute '%s'" % propname)


def set_exposed_property_value(obj, propname, value, only_exposed=True):
    """
    Sets the value of an @exposed @property.
    If the requested property is not a @property or not exposed,
    an AttributeError is raised instead.
    """
    v = getattr(obj.__class__, propname)
    if inspect.isdatadescriptor(v):
        pfunc = v.fget or v.fset or v.fdel
        if v.fset and getattr(pfunc, "_pyroExposed", not only_exposed):
            return v.fset(obj, value)
    raise AttributeError("attempt to access unexposed or unknown remote attribute '%s'" % propname)


_private_dunder_methods = frozenset([
    "__init__", "__call__", "__new__", "__del__", "__repr__",
    "__str__", "__format__", "__nonzero__", "__bool__", "__coerce__",
    "__cmp__", "__eq__", "__ne__", "__hash__",
    "__dir__", "__enter__", "__exit__", "__copy__", "__deepcopy__", "__sizeof__",
    "__getattr__", "__setattr__", "__hasattr__", "__getattribute__", "__delattr__",
    "__instancecheck__", "__subclasscheck__", "__getinitargs__", "__getnewargs__",
    "__getstate__", "__setstate__", "__reduce__", "__reduce_ex__",
    "__getstate_for_dict__", "__setstate_from_dict__", "__subclasshook__"
])


def is_private_attribute(attr_name):
    """returns if the attribute name is to be considered private or not."""
    if attr_name in _private_dunder_methods:
        return True
    if not attr_name.startswith('_'):
        return False
    if len(attr_name) > 4 and attr_name.startswith("__") and attr_name.endswith("__"):
        return False
    return True
