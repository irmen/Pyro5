import random
import time
from Pyro5.api import expose, Daemon, locate_ns


@expose
class StockMarket(object):
    def __init__(self, marketname, symbols):
        """
        Initialize market symbols.

        Args:
            self: (todo): write your description
            marketname: (str): write your description
            symbols: (str): write your description
        """
        self._name = marketname
        self._symbols = symbols

    def quotes(self):
        """
        Returns a random quotes.

        Args:
            self: (todo): write your description
        """
        while True:
            symbol = random.choice(self.symbols)
            yield symbol, round(random.uniform(5, 150), 2)
            time.sleep(random.random()/2.0)

    @property
    def name(self):
        """
        The name of the name

        Args:
            self: (todo): write your description
        """
        return self._name

    @property
    def symbols(self):
        """
        A set of symbols that symbols.

        Args:
            self: (todo): write your description
        """
        return self._symbols


if __name__ == "__main__":
    nasdaq = StockMarket("NASDAQ", ["AAPL", "CSCO", "MSFT", "GOOG"])
    newyork = StockMarket("NYSE", ["IBM", "HPQ", "BP"])
    # for example purposes we will access the daemon and name server ourselves
    with Daemon() as daemon:
        nasdaq_uri = daemon.register(nasdaq)
        newyork_uri = daemon.register(newyork)
        with locate_ns() as ns:
            ns.register("example.stockmarket.nasdaq", nasdaq_uri)
            ns.register("example.stockmarket.newyork", newyork_uri)
        print("Stockmarkets available.")
        daemon.requestLoop()
