import sys
import datetime
import Pyro5.api
import Pyro5.errors
from customdata import CustomData


sys.excepthook = Pyro5.errors.excepthook

# teach Serpent how to serialize our data class
Pyro5.api.SerializerBase.register_class_to_dict(CustomData, CustomData.to_dict)


with Pyro5.api.Proxy("PYRONAME:example.blobdispatcher") as dispatcher:
    while True:
        topic = input("Enter topic to send data on (just enter to quit) ").strip()
        if not topic:
            break
        # create our custom data object and send it through the dispatcher
        data = CustomData(42, "hello world", datetime.datetime.now())
        dispatcher.process_blob(Pyro5.api.SerializedBlob(topic, data))
        print("processed")
