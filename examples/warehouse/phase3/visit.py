# This is the code that visits the warehouse.
import sys
import Pyro5.errors
from Pyro5.api import Proxy
from person import Person


sys.excepthook = Pyro5.errors.excepthook

warehouse = Proxy("PYRONAME:example.warehouse")
janet = Person("Janet")
henry = Person("Henry")
janet.visit(warehouse)
henry.visit(warehouse)
