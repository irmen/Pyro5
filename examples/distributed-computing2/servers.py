import string
import time
from collections import Counter
from itertools import cycle, zip_longest
from concurrent import futures
from Pyro5.api import expose, serve, locate_ns, Proxy, config
import Pyro5.errors


class WordCounter(object):
    filter_words = {'a', 'an', 'at', 'the', 'i', 'he', 'she', 's', 'but', 'was', 'has', 'had', 'have', 'and',
                    'are', 'as', 'be', 'by', 'for', 'if', 'in', 'is', 'it', 'of', 'or', 'that',
                    'the', 'to', 'with', 'his', 'all', 'any', 'this', 'that', 'not', 'from', 'on',
                    'me', 'him', 'her', 'their', 'so', 'you', 'there', 'now', 'then', 'no', 'yes',
                    'one', 'were', 'they', 'them', 'which', 'what', 'when', 'who', 'how', 'where', 'some', 'my',
                    'into', 'up', 'out', 'some', 'we', 'us', 't', 'do'}
    trans_punc = {ord(punc): u' ' for punc in string.punctuation}

    @expose
    def count(self, lines):
        counts = Counter()
        for num, line in enumerate(lines):
            if line:
                line = line.translate(self.trans_punc).lower()
                interesting_words = [w for w in line.split() if w.isalpha() and w not in self.filter_words]
                counts.update(interesting_words)
            if num % 10 == 0:
                time.sleep(0.01)  # artificial delay to show execution time differences (and make this not cpu-bound)
        return counts


def grouper(n, iterable, padvalue=None):
    """grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"""
    return zip_longest(*[iter(iterable)]*n, fillvalue=padvalue)


class Dispatcher(object):
    def count_chunk(self, counter, chunk):
        with Proxy(counter) as c:
            return c.count(chunk)

    @expose
    def count(self, lines):
        # use the name server's prefix lookup to get all registered wordcounters
        with locate_ns() as ns:
            all_counters = ns.list(prefix="example.dc2.wordcount.")

        # chop the text into chunks that can be distributed across the workers
        # uses futures so that it runs the counts in parallel
        # counter is selected in a round-robin fashion from list of all available counters
        with futures.ThreadPoolExecutor() as pool:
            roundrobin_counters = cycle(all_counters.values())
            tasks = []
            for chunk in grouper(200, lines):
                tasks.append(pool.submit(self.count_chunk, next(roundrobin_counters), chunk))

            # gather the results
            print("Collecting %d results (counted in parallel)..." % len(tasks))
            totals = Counter()
            for task in futures.as_completed(tasks):
                try:
                    totals.update(task.result())
                except Pyro5.errors.CommunicationError as x:
                    raise Pyro5.errors.PyroError("Something went wrong in the server when collecting the responses: "+str(x))
            return totals


if __name__ == "__main__":
    print("Spinning up 5 word counters, and 1 dispatcher.")
    config.SERVERTYPE = "thread"
    serve(
        {
            WordCounter(): "example.dc2.wordcount.1",
            WordCounter(): "example.dc2.wordcount.2",
            WordCounter(): "example.dc2.wordcount.3",
            WordCounter(): "example.dc2.wordcount.4",
            WordCounter(): "example.dc2.wordcount.5",
            Dispatcher:    "example.dc2.dispatcher"
        }, verbose=False
    )
