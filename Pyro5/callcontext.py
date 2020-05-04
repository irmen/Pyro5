"""
Deals with the context variables of a Pyro call.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import threading
from . import errors


class _CallContext(threading.local):
    """call context thread local"""
    def __init__(self):
        # per-thread initialization
        self.client = None
        self.client_sock_addr = None
        self.seq = 0
        self.msg_flags = 0
        self.serializer_id = 0
        self.annotations = {}
        self.response_annotations = {}
        self.correlation_id = None

    def to_global(self):
        return dict(self.__dict__)

    def from_global(self, values):
        self.client = values["client"]
        self.seq = values["seq"]
        self.msg_flags = values["msg_flags"]
        self.serializer_id = values["serializer_id"]
        self.annotations = values["annotations"]
        self.response_annotations = values["response_annotations"]
        self.correlation_id = values["correlation_id"]
        self.client_sock_addr = values["client_sock_addr"]

    def track_resource(self, resource):
        """keep a weak reference to the resource to be tracked for this connection"""
        if self.client:
            self.client.tracked_resources.add(resource)
        else:
            raise errors.PyroError("cannot track resource on a connectionless call")

    def untrack_resource(self, resource):
        """no longer track the resource for this connection"""
        if self.client:
            self.client.tracked_resources.discard(resource)
        else:
            raise errors.PyroError("cannot untrack resource on a connectionless call")


current_context = _CallContext()
"""the thread-local context object for the current Pyro call"""
