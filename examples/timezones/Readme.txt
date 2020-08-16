PREREQUISITES:
install the 'pytz', 'python-dateutil' and 'pendulum' libraries

This example shows how datetime and timezones could be handled.
The default serpent serializer will serialize them as a string in ISO date/time format.
You will have to either parse the string yourself,
or perhaps use a custom serializer/deserializer (not shown in this example).
