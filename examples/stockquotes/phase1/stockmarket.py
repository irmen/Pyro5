import random
import time


class StockMarket(object):
    def __init__(self, marketname, symbols):
        """
        Initialize the symbols.

        Args:
            self: (todo): write your description
            marketname: (str): write your description
            symbols: (str): write your description
        """
        self.name = marketname
        self.symbols = symbols

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
