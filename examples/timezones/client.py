import pendulum
import datetime
from Pyro5.api import Proxy


uri = input("What is the server uri? ").strip()
fmt = '%Y-%m-%d %H:%M:%S %Z%z'
print("local time without timezone: ", datetime.datetime.now().strftime(fmt))


with Proxy(uri) as serv:
    print("\n1. no timezone")
    datestr = serv.echo(datetime.datetime.now())
    print("Got from server:", repr(datestr))
    dt = pendulum.parse(datestr)
    print("   parsed:", repr(dt))

    print("\n2. PyTz timezones")
    datestr = serv.pytz()
    print("Got from server:", repr(datestr))
    dt = pendulum.parse(datestr)
    print("   parsed:", repr(dt))

    print("\n3. DateUtil timezones")
    datestr = serv.dateutil()
    print("Got from server:", repr(datestr))
    dt = pendulum.parse(datestr)
    print("   parsed:", repr(dt))

    print("\n4. Pendulum timezones")
    datestr = serv.pendulum()
    print("Got from server:", repr(datestr))
    dt = pendulum.parse(datestr)
    print("   parsed:", repr(dt))
    print()
