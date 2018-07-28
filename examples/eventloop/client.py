from Pyro5.api import Proxy


with Proxy("PYRONAME:example.eventloop.server") as proxy:
    print("5*11=%d" % proxy.multiply(5, 11))
    print("'x'*10=%s" % proxy.multiply('x', 10))

    input("press enter to do a loop of some more calls:")
    for i in range(1, 20):
        print("2*i=%d" % proxy.multiply(2, i))
        print("'@'*i=%s" % proxy.multiply('@', i))
