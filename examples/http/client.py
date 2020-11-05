import json
import re
import pprint
from urllib.request import urlopen, Request
from urllib.error import HTTPError


def get_charset(req):
    """
    Get the charset of a request.

    Args:
        req: (todo): write your description
    """
    charset = "utf-8"
    match = re.match(r".* charset=(.+)", req.getheader("Content-Type"))
    if match:
        charset = match.group(1)
    return charset


def pyro_call(object_name, method, callback):
    """
    Calls an xml - rpc method.

    Args:
        object_name: (str): write your description
        method: (str): write your description
        callback: (todo): write your description
    """
    request = Request("http://127.0.0.1:8080/pyro/{0}/{1}".format(object_name, method),
                      # headers={"x-pyro-options": "oneway", "x-pyro-gateway-key": "secretgatewaykey"}
                      )
    with urlopen(request) as req:
        charset = get_charset(req)
        data = req.read().decode(charset)
    if data:
        callback(json.loads(data))
    else:
        callback(None)


def write_result(result):
    """
    Write result to the result file.

    Args:
        result: (str): write your description
    """
    pprint.pprint(result, width=40)

try:
    print("\nLIST--->")
    pyro_call("Pyro.NameServer", "list", write_result)
except HTTPError as x:
    print("Error:", x)
    print("Error response data:", x.read())

try:
    print("\nMETA--->")
    pyro_call("Pyro.NameServer", "$meta", write_result)
except HTTPError as x:
    print("Error:", x)
    print("Error response data:", x.read())

try:
    print("\nLOOKUP--->")
    pyro_call("Pyro.NameServer", "lookup?name=Pyro.NameServer", write_result)
except HTTPError as x:
    print("Error:", x)
    print("Error response data:", x.read())

try:
    print("\nONEWAY_SLOW--->")
    pyro_call("test.echoserver", "oneway_slow", write_result)
except HTTPError as x:
    print("Error:", x)
    print("Error response data:", x.read())

try:
    print("\nSLOW--->")
    pyro_call("test.echoserver", "slow", write_result)
except HTTPError as x:
    print("Error:", x)
    print("Error response data:", x.read())

# Note that there is a nicer way to pass the parameters, you can probably
# grab them from a function's vargs and/or kwargs and convert those to
# a querystring using the appropriate library function.
# Then you can call the method as usual and don't have to worry about adding the querystring
# (or sticking it in a POST request if the params are too large)...
