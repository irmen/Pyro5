from Pyro5.compatibility import Pyro4
import Pyro4


obj = Pyro4.Proxy("PYRONAME:example.chain.A")
print("Result=%s" % obj.process(["hello"]))
