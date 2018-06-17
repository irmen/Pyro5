# This is the code that visits the warehouse.
from Pyro5.api import Proxy
from person import Person


uri = input("Enter the uri of the warehouse: ").strip()
warehouse = Proxy(uri)
janet = Person("Janet")
henry = Person("Henry")
janet.visit(warehouse)
henry.visit(warehouse)
