from Pyro5.api import expose, oneway


@expose
class bench(object):
    def length(self, string):
        """
        Returns the length of the string.

        Args:
            self: (todo): write your description
            string: (str): write your description
        """
        return len(string)

    def timestwo(self, value):
        """
        Returns the timestwo.

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        return value * 2

    def bigreply(self):
        """
        Return bigreply

        Args:
            self: (todo): write your description
        """
        return 'BIG REPLY' * 500

    def bigarg(self, arg):
        """
        Returns the bigarg for arg.

        Args:
            self: (todo): write your description
            arg: (str): write your description
        """
        return len(arg)

    def manyargs(self, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15):
        """
        Many arguments

        Args:
            self: (todo): write your description
            a1: (array): write your description
            a2: (array): write your description
            a3: (array): write your description
            a4: (array): write your description
            a5: (array): write your description
            a6: (array): write your description
            a7: (array): write your description
            a8: (array): write your description
            a9: (array): write your description
            a10: (array): write your description
            a11: (array): write your description
            a12: (array): write your description
            a13: (array): write your description
            a14: (array): write your description
            a15: (array): write your description
        """
        return a1 + a2 + a3 + a4 + a5 + a6 + a7 + a8 + a9 + a10 + a11 + a12 + a13 + a14 + a15

    def noreply(self, arg):
        """
        Nore a : param : param

        Args:
            self: (todo): write your description
            arg: (str): write your description
        """
        pass

    def varargs(self, *args):
        """
        Returns the variable length.

        Args:
            self: (todo): write your description
        """
        return len(args)

    def keywords(self, **args):
        """
        Return a list of keywords.

        Args:
            self: (todo): write your description
        """
        return args

    def echo(self, *args):
        """
        Echo the given args.

        Args:
            self: (todo): write your description
        """
        return args

    @oneway
    def oneway(self, *args):
        """
        Calls on oneway.

        Args:
            self: (todo): write your description
        """
        # oneway doesn't return anything
        pass
