"""
This is the producer for the 'many topics' messages example.
"""
import time
import random
import sys
import Pyro5.errors
from Pyro5.api import Proxy
from messagebus import PYRO_MSGBUS_NAME

sys.excepthook = Pyro5.errors.excepthook

# add a bunch of topics to the bus
bus = Proxy("PYRONAME:"+PYRO_MSGBUS_NAME)
for letter in "abcdefghijklmnopqrstuvwxyz":
    bus.add_topic("msg.topic.%s" % letter)

print("publishing messages on a random topic")
seq = 1
while True:
    time.sleep(0.05)
    letter = random.choice("abcdefghijklmnopqrstuvwxyz")
    topic = "msg.topic.%s" % letter
    bus.send(topic, "message %d" % seq)
    seq += 1
    print("", letter, seq, end="\r")
