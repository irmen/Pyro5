import sys
import datetime
from Pyro5.compatibility import Pyro4
import Pyro4.util
import Pyro4.core
import Pyro4
import Pyro5.client
from customdata import CustomData


sys.excepthook = Pyro4.util.excepthook

# teach Serpent how to serialize our data class
Pyro4.util.SerializerBase.register_class_to_dict(CustomData, CustomData.to_dict)


with Pyro4.Proxy("PYRONAME:example.blobdispatcher") as dispatcher:
    while True:
        topic = input("Enter topic to send data on (just enter to quit) ").strip()
        if not topic:
            break
        # create our custom data object and send it through the dispatcher
        data = CustomData(42, "hello world", datetime.datetime.now())

        # @todo FIX THIS -- CRASHES WITH SOCKET ERROR NOT ENOUGH DATA
        dispatcher.process_blob(Pyro5.client.SerializedBlob(topic, data))
        print("processed")
