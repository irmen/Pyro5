"""
This is a subscriber meant for the 'weather' messages example.
It uses a custom code loop to get and process messages.
"""
import sys
import threading
import time
import Pyro5.errors
from Pyro5.api import expose, Daemon
from messagebus.messagebus import Subscriber

sys.excepthook = Pyro5.errors.excepthook


@expose
class Subber(Subscriber):
    def consume_message(self, topic, message):
        """
        Consume a message

        Args:
            self: (todo): write your description
            topic: (str): write your description
            message: (str): write your description
        """
        # In this case, this consume message method is called by our own code loop.
        print("\nPROCESSING MESSAGE:")
        print("   topic:", topic)
        print("   msgid:", message.msgid)
        print(" created:", message.created)
        print("    data:", message.data)

    def manual_message_loop(self):
        """
        Manage message loop.

        Args:
            self: (todo): write your description
        """
        print("Entering manual message processing loop (5 messages).")
        processed = 0
        while processed < 5:
            time.sleep(0.5)
            print("\nApprox. number of received messages:", self.received_messages.qsize())
            topic, message = self.received_messages.get()   # get a message from the queue (they are put there by the Pyro messagebus)
            self.consume_message(topic, message)
            processed += 1
        print("\nEnd.")


hostname = input("hostname to bind on (empty=localhost): ").strip() or "localhost"

# create a messagebus subscriber that uses manual message retrieval (via explicit call)
# because we're doing the message loop ourselves, the Pyro daemon has to run in a separate thread
subber = Subber(auto_consume=False)
d = Daemon(host=hostname)
d.register(subber)
daemon_thread = threading.Thread(target=d.requestLoop)
daemon_thread.daemon = True
daemon_thread.start()
topics = subber.bus.topics()
print("Topics on the bus: ", topics)
print("Subscribing to weather-forecast.")

subber.bus.subscribe("weather-forecast", subber)
# note: we subscribe on the bus *after* registering the subber as a Pyro object
# this results in Pyro automatically making a proxy for the subber
print("Subscribed on weather-forecast")

# run the manual message loop
print("Entering message loop, you should see the msg count increasing.")
subber.manual_message_loop()
subber.bus.unsubscribe("weather-forecast", subber)
print("Unsubscribed from the topic.")
print("Entering message loop again, you should see the msg count decrease.")
subber.manual_message_loop()
