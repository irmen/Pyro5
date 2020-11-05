import datetime
import pytz
import dateutil.tz
import pendulum
from Pyro5.api import expose, serve


fmt = '%Y-%m-%d %H:%M:%S %Z%z'


@expose
class Server(object):
    def echo(self, date):
        """
        Echo the given date.

        Args:
            self: (todo): write your description
            date: (todo): write your description
        """
        print("RETURNING:", repr(date))
        return date

    def pytz(self):
        """
        Return a datetime.

        Args:
            self: (todo): write your description
        """
        tz_nl = pytz.timezone("Europe/Amsterdam")
        result = tz_nl.localize(datetime.datetime.now())
        print("RETURNING:", repr(result))
        return result

    def dateutil(self):
        """
        Returns a datetime.

        Args:
            self: (todo): write your description
        """
        tz_nl = dateutil.tz.gettz("Europe/Amsterdam")
        result = datetime.datetime.now(tz_nl)
        print("RETURNING:", repr(result))
        return result

    def pendulum(self):
        """
        Add a new timezone to the current timezone.

        Args:
            self: (todo): write your description
        """
        tz_nl = pendulum.now("Europe/Amsterdam")
        print("RETURNING:", repr(tz_nl))
        return tz_nl


# main program

serve({
    Server: "example.timezones"
}, use_ns=False)
