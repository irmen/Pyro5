import datetime
import pytz
import dateutil.tz
import pendulum
from Pyro5.api import expose, serve


fmt = '%Y-%m-%d %H:%M:%S %Z%z'


@expose
class Server(object):
    def echo(self, date):
        print("RETURNING:", repr(date))
        return date

    def pytz(self):
        tz_nl = pytz.timezone("Europe/Amsterdam")
        result = tz_nl.localize(datetime.datetime.now())
        print("RETURNING:", repr(result))
        return result

    def dateutil(self):
        tz_nl = dateutil.tz.gettz("Europe/Amsterdam")
        result = datetime.datetime.now(tz_nl)
        print("RETURNING:", repr(result))
        return result

    def pendulum(self):
        tz_nl = pendulum.now("Europe/Amsterdam")
        print("RETURNING:", repr(tz_nl))
        return tz_nl


# main program

serve({
    Server: "example.timezones"
}, use_ns=False)
