import datetime
import traceback
from Pyro5.api import Proxy, config


uri = input("What is the server uri? ").strip()
fmt = '%Y-%m-%d %H:%M:%S %Z%z'
print("local time without timezone: ", datetime.datetime.now().strftime(fmt))


def test():
    with Proxy(uri) as serv:
        print("\nFIRST: no timezone")
        try:
            date1 = serv.echo(datetime.datetime.now())
            print("Got from server:", date1)
            print("{0}\n  {1} ({2})".format(date1, repr(date1), type(date1)))
            if isinstance(date1, datetime.datetime):
                if hasattr(date1, "tzinfo"):
                    print("    tzinfo =", date1.tzinfo)
                else:
                    print("    no tzinfo attribute")
        except Exception:
            print("ERROR!")
            traceback.print_exc()

        print("\nSECOND: PyTz timezones")
        try:
            date1 = serv.pytz()
            print("Got from server:", date1)
            if isinstance(date1, datetime.datetime):
                assert isinstance(date1.tzinfo, datetime.tzinfo)
                print("{0}\n  {1} ({2})\n    {3}".format(date1, date1.tzinfo, type(date1.tzinfo), date1.strftime(fmt)))
                date2 = serv.echo(date1)
                print("{0}\n  {1} ({2})\n    {3}".format(date2, date2.tzinfo, type(date2.tzinfo), date2.strftime(fmt)))
                assert date1 == date2
        except Exception:
            print("ERROR!")
            traceback.print_exc()

        print("\nTHIRD: DateUtil timezones")
        try:
            date1 = serv.dateutil()
            print("Got from server:", date1)
            if isinstance(date1, datetime.datetime):
                assert isinstance(date1.tzinfo, datetime.tzinfo)
                print("{0}\n  {1} ({2})\n    {3}".format(date1, date1.tzinfo, type(date1.tzinfo), date1.strftime(fmt)))
                date2 = serv.echo(date1)
                print("{0}\n  {1} ({2})\n    {3}".format(date2, date2.tzinfo, type(date2.tzinfo), date2.strftime(fmt)))
                assert date1 == date2
        except Exception:
            print("ERROR!")
            traceback.print_exc()

        print("\nFOURTH: Pendulum timezones")
        try:
            date1 = serv.pendulum()
            print("Got from server:", date1)
            if isinstance(date1, datetime.datetime):
                assert isinstance(date1.tzinfo, datetime.tzinfo)
                print("{0}\n  {1} ({2})\n    {3}".format(date1, date1.tzinfo, type(date1.tzinfo), date1.strftime(fmt)))
                date2 = serv.echo(date1)
                print("{0}\n  {1} ({2})\n    {3}".format(date2, date2.tzinfo, type(date2.tzinfo), date2.strftime(fmt)))
                assert date1 == date2
        except Exception:
            print("ERROR!")
            traceback.print_exc()


# serpent.
print("\n******* serpent *******")
config.SERIALIZER = "serpent"
try:
    test()
except Exception:
    import traceback
    traceback.print_exc()

# json.
print("\n******* json *******")
config.SERIALIZER = "json"
try:
    test()
except Exception:
    import traceback
    traceback.print_exc()

# msgpack.
print("\n******* msgpack *******")
config.SERIALIZER = "msgpack"
try:
    test()
except Exception:
    import traceback
    traceback.print_exc()

# marshal.
print("\n******* marshal *******")
config.SERIALIZER = "marshal"
try:
    test()
except Exception:
    import traceback
    traceback.print_exc()

