from Pyro5.api import Proxy


obj = Proxy("PYRONAME:example.chain.A")
print("Result=%s" % obj.process(["hello"]))
