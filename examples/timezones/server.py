import datetime
import pytz
import dateutil.tz
import pendulum
from Pyro5.api import expose, serve


fmt = '%Y-%m-%d %H:%M:%S %Z%z'


@expose
class Server(object):
    def echo(self, date):
        print("ECHO:")
        print(" [raw] ", repr(date))
        if hasattr(date, "isoformat"):
            print(" [iso] ", date.isoformat())
        return date

    def pytz(self):
        tz_nl = pytz.timezone("Europe/Amsterdam")
        return tz_nl.localize(datetime.datetime.now())

    def dateutil(self):
        tz_nl = dateutil.tz.gettz("Europe/Amsterdam")
        return datetime.datetime.now(tz_nl)

    def pendulum(self):
        tz_nl = pendulum.now("Europe/Amsterdam")
        return tz_nl


# main program

serve({
    Server: "example.timezones"
}, use_ns=False)
