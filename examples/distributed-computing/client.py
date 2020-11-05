import random
from Pyro5.api import Proxy, register_dict_to_class
from workitem import Workitem


# For 'workitem.Workitem' we register a deserialization hook to be able to get these back from Pyro
register_dict_to_class("workitem.Workitem", Workitem.from_dict)

NUMBER_OF_ITEMS = 40


def main():
    """
    Main function.

    Args:
    """
    print("\nThis program will calculate Prime Factorials of a bunch of random numbers.")
    print("The more workers you will start (on different cpus/cores/machines),")
    print("the faster you will get the complete list of results!\n")
    with Proxy("PYRONAME:example.distributed.dispatcher") as dispatcher:
        placework(dispatcher)
        numbers = collectresults(dispatcher)
    printresults(numbers)


def placework(dispatcher):
    """
    Print a random number of a random number of the number.

    Args:
        dispatcher: (todo): write your description
    """
    print("placing work items into dispatcher queue.")
    for i in range(NUMBER_OF_ITEMS):
        number = random.randint(3211, 4999999) * random.randint(3211, 999999)
        item = Workitem(i + 1, number)
        dispatcher.putWork(item)


def collectresults(dispatcher):
    """
    Collect the results of the number of the queue.

    Args:
        dispatcher: (todo): write your description
    """
    print("getting results from dispatcher queue.")
    numbers = {}
    while len(numbers) < NUMBER_OF_ITEMS:
        try:
            item = dispatcher.getResult()
        except ValueError:
            print("Not all results available yet (got %d out of %d). Work queue size: %d" %
                  (len(numbers), NUMBER_OF_ITEMS, dispatcher.workQueueSize()))
        else:
            print("Got result: %s (from %s)" % (item, item.processedBy))
            numbers[item.data] = item.result

    if dispatcher.resultQueueSize() > 0:
        print("there's still stuff in the dispatcher result queue, that is odd...")
    return numbers


def printresults(numbers):
    """
    Print the number of numbers.

    Args:
        numbers: (dict): write your description
    """
    print("\nComputed Prime Factorials follow:")
    for (number, factorials) in numbers.items():
        print("%d --> %s" % (number, factorials))


if __name__ == "__main__":
    main()
