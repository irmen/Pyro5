"""
This is the publisher meant for the 'weather' messages example.
"""
import time
import random
import sys
from Pyro5.compatibility import Pyro4
import Pyro4
import Pyro4.errors
from Pyro4.util import excepthook
from messagebus import PYRO_MSGBUS_NAME

sys.excepthook = excepthook

location = input("Give city or country to use as location: ").strip() or 'Amsterdam'

bus = Pyro4.Proxy("PYRONAME:"+PYRO_MSGBUS_NAME)
bus.add_topic("weather-forecast")

while True:
    time.sleep(0.01)
    forecast = (location, random.choice(["sunny", "cloudy", "storm", "rainy", "hail", "thunder", "calm", "mist", "cold", "hot"]))
    print("Forecast:", forecast)
    try:
        bus.send("weather-forecast", forecast)
    except Pyro4.errors.CommunicationError:
        print("connection to the messagebus is lost, reconnecting...")
        bus._pyroReconnect()
