import sys
import Pyro5.api
import Pyro5.errors

test = Pyro5.api.Proxy("PYRONAME:example.exceptions")

print(test.div(2.0, 9.0))
try:
    print(2 // 0)
except ZeroDivisionError as x:
    print("DIVIDE BY ZERO: ", x)
try:
    print(test.div(2, 0))
except ZeroDivisionError as x:
    print("DIVIDE BY ZERO: ", x)
try:
    result = test.error()
    print("%r, %s" % (result, result))
except ValueError as x:
    print("VALUERROR: ", x)
try:
    result = test.error2()
    print("%r, %s" % (result, result))
except ValueError as x:
    print("VALUERROR: ", x)
try:
    result = test.othererr()
    print("%r, %s" % (result, result))
except Exception as x:
    print("ANOTHER ERROR: ", x)
try:
    result = test.onewayerr()
    print("oneway call simply succeeded")
except Exception as x:
    print("SHOULD NOT HAPPEN: exception from oneway call", x)
try:
    result = test.unserializable()
    print("%r, %s" % (result, result))
except Exception as x:
    print("UNSERIALIZABLE ERROR: ", x)

print("\n*** invoking server method that crashes, catching traceback ***")
try:
    print(test.complexerror())
except Exception as x:
    print("CAUGHT ERROR  >>> ", x)
    print("Printing Pyro traceback >>>>>>")
    print("".join(Pyro5.errors.get_pyro_traceback()))
    print("<<<<<<< end of Pyro traceback")

print("\n*** installing pyro's excepthook")
sys.excepthook = Pyro5.errors.excepthook
print("*** invoking server method that crashes, not catching anything ***")
print(test.complexerror())  # due to the excepthook, the exception will show the pyro error
