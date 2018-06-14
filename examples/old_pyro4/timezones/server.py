import datetime
import pytz
import dateutil.tz
from Pyro5.compatibility import Pyro4
import Pyro4


fmt = '%Y-%m-%d %H:%M:%S %Z%z'


@Pyro4.expose
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

# main program

Pyro4.Daemon.serveSimple({
    Server: "example.timezones"
}, ns=False)
