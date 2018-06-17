"""
This is the subscriber for the 'many topics' messages example.
For code with more explanations, see the regular 'weather' message example code.
"""
import os
import time
import threading
from operator import itemgetter
from Pyro5.api import expose, Daemon
from messagebus.messagebus import Subscriber


@expose
class Subber(Subscriber):
    def init_counters(self, topics):
        self.message_counter = {}
        self.last_message = {}
        for t in topics:
            self.message_counter[t] = 0
            self.last_message[t] = None

    def consume_message(self, topic, message):
        self.message_counter[topic] += 1
        self.last_message[topic] = message


def clear_screen():
    os.system(['clear', 'cls'][os.name == 'nt'])


subber = Subber()
d = Daemon()
d.register(subber)
daemon_thread = threading.Thread(target=d.requestLoop)
daemon_thread.daemon = True
daemon_thread.start()

# mass subscribe to all available topics
topics = list(sorted(subber.bus.topics()))
subber.init_counters(topics)
for t in topics:
    subber.bus.subscribe(t, subber)

# show a table of the active topics on the bus
while True:
    clear_screen()
    print(time.ctime(), "-- active topics on the messagebus:")
    print("{:20} : {:5}     {}         {}".format("topic", "count", "last_recv", "last message data"))
    for topic, count in sorted(subber.message_counter.items(), key=itemgetter(1), reverse=True):
        msg = subber.last_message[topic]
        if msg:
            print("{:20} : {:5d}  -  {}   {!r:.20}".format(topic, count, msg.created.time(), msg.data))
        else:
            print("{:20} : {:5d}".format(topic, count))
    print("(restart me to refresh the list of topics)")
    time.sleep(1)
