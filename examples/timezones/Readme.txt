This example exercises the support for pytz/dateutil timezones in the serializers.
You'll see that this is quite problematic as the tz info is not really a standard
extension, or some serializers may fail to serialize a datetime object at all.

The only solution is to convert back to a datetime without tz info (so perhaps
normalize them all to UTC) before transferring, or avoiding datetime objects entirely...


PREREQUISITES:
install the 'pytz', 'python-dateutil' and 'pendulum' libraries
