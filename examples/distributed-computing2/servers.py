import string
import time
from collections import Counter
from itertools import cycle, zip_longest
from Pyro5.api import expose, Daemon, locate_ns, Proxy, config
import Pyro5.errors


@expose
class WordCounter(object):
    filter_words = {'a', 'an', 'at', 'the', 'i', 'he', 'she', 's', 'but', 'was', 'has', 'had', 'have', 'and',
                    'are', 'as', 'be', 'by', 'for', 'if', 'in', 'is', 'it', 'of', 'or', 'that',
                    'the', 'to', 'with', 'his', 'all', 'any', 'this', 'that', 'not', 'from', 'on',
                    'me', 'him', 'her', 'their', 'so', 'you', 'there', 'now', 'then', 'no', 'yes',
                    'one', 'were', 'they', 'them', 'which', 'what', 'when', 'who', 'how', 'where', 'some', 'my',
                    'into', 'up', 'out', 'some', 'we', 'us', 't', 'do'}
    trans_punc = {ord(punc): u' ' for punc in string.punctuation}

    def count(self, lines):
        counts = Counter()
        for num, line in enumerate(lines):
            if line:
                line = line.translate(self.trans_punc).lower()
                interesting_words = [w for w in line.split() if w.isalpha() and w not in self.filter_words]
                counts.update(interesting_words)
            if num % 10 == 0:
                time.sleep(0.01)  # artificial delay to dramatize execution time differences
        return counts


def grouper(n, iterable, padvalue=None):
    """grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"""
    return zip_longest(*[iter(iterable)]*n, fillvalue=padvalue)


@expose
class Dispatcher(object):
    def count(self, lines):
        # use the name server's prefix lookup to get all registered wordcounters
        with locate_ns() as ns:
            all_counters = ns.list(prefix="example.dc2.wordcount.")
        counters = [Proxy(uri) for uri in all_counters.values()]
        #for c in counters:
        #    c._pyroAsync()   # set proxy in asynchronous mode
        # @todo alternative for ASYNC to run it in parallel
        roundrobin_counters = cycle(counters)

        # chop the text into chunks that can be distributed across the workers
        # uses asynchronous proxy so that we can hand off everything in parallel
        # counter is selected in a round-robin fashion from list of all available counters
        # (This is a brain dead way because it doesn't scale - all the asynchronous calls are hogging
        # the worker threads in the server. That's why we've increased that a lot at the start
        # of this file, just for the sake of this example!)
        async_results = []
        for chunk in grouper(100, lines):
            counter = next(roundrobin_counters)
            result = counter.count(chunk)
            async_results.append(result)

        # gather the results
        print("Collecting %d results..." % len(async_results))
        totals = Counter()
        for result in async_results:
            try:
                totals.update(result)     # @todo alternative for ASYNC results to run it in parallel
            except Pyro5.errors.CommunicationError as x:
                raise Pyro5.errors.PyroError("Something went wrong in the server when collecting the async responses: "+str(x))
        for proxy in counters:
            proxy._pyroRelease()
        return totals


if __name__ == "__main__":
    print("Spinning up 5 wordcounters, and 1 dispatcher.")
    config.SERVERTYPE = "thread"
    Daemon.serveSimple(
        {
            WordCounter(): "example.dc2.wordcount.1",
            WordCounter(): "example.dc2.wordcount.2",
            WordCounter(): "example.dc2.wordcount.3",
            WordCounter(): "example.dc2.wordcount.4",
            WordCounter(): "example.dc2.wordcount.5",
            Dispatcher:    "example.dc2.dispatcher"
        }, verbose=False
    )
