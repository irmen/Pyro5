import Pyro5.api
from awesome_thirdparty_library import AwesomeClass


# expose the class from the library using @expose as wrapper function:
ExposedClass = Pyro5.api.expose(AwesomeClass)


with Pyro5.api.Daemon() as daemon:
    # register the wrapped class instead of the library class itself:
    uri = daemon.register(ExposedClass, "example.thirdpartylib")
    print("wrapped class registered, uri: ", uri)
    daemon.requestLoop()
