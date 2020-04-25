import Pyro5.api
import Pyro5.core
import Pyro5.client
import Pyro5.server
import Pyro5.nameserver
import Pyro5.callcontext
import Pyro5.serializers
from Pyro5.serializers import SerializerBase


def test_api():
    assert hasattr(Pyro5.api, "__version__")
    assert Pyro5.api.config.SERIALIZER == "serpent"
    assert Pyro5.api.URI is Pyro5.core.URI
    assert Pyro5.api.Proxy is Pyro5.client.Proxy
    assert Pyro5.api.Daemon is Pyro5.server.Daemon
    assert Pyro5.api.start_ns is Pyro5.nameserver.start_ns
    assert Pyro5.api.current_context is Pyro5.callcontext.current_context
    assert Pyro5.api.register_dict_to_class == SerializerBase.register_dict_to_class
    assert Pyro5.api.register_class_to_dict == SerializerBase.register_class_to_dict
    assert Pyro5.api.unregister_dict_to_class == SerializerBase.unregister_dict_to_class
    assert Pyro5.api.unregister_class_to_dict == SerializerBase.unregister_class_to_dict
