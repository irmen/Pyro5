import Pyro5.api
import Pyro5.core


class TestApi:
    def test_api(self):
        assert hasattr(Pyro5.api, "__version__")
        assert Pyro5.api.URI is Pyro5.core.URI

