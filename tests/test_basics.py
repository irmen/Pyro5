import Pyro5.api


class TestBasics:
    def test_api(self):
        assert hasattr(Pyro5.api, "__version__")
