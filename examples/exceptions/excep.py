from Pyro5.api import expose, oneway


@expose
class TestClass(object):
    def div(self, arg1, arg2):
        """
        Divide two arguments.

        Args:
            self: (todo): write your description
            arg1: (int): write your description
            arg2: (int): write your description
        """
        return arg1 / arg2

    def error(self):
        """
        Set the error message.

        Args:
            self: (todo): write your description
        """
        raise ValueError('a valueerror! Great!')

    def error2(self):
        """
        Returns the error value.

        Args:
            self: (todo): write your description
        """
        return ValueError('a valueerror! Great!')

    def othererr(self):
        """
        Èi̇·åıĸotrr.

        Args:
            self: (todo): write your description
        """
        raise RuntimeError('a runtime error!')

    @oneway
    def onewayerr(self):
        """
        Èi̇·åıĸæį¢æīģł

        Args:
            self: (todo): write your description
        """
        raise ValueError('error in oneway call!')

    def complexerror(self):
        """
        Crerror.

        Args:
            self: (todo): write your description
        """
        x = Foo()
        x.crash()

    def unserializable(self):
        """
        Unserialize a serializable object.

        Args:
            self: (todo): write your description
        """
        return TestClass.unserializable


class Foo(object):
    def crash(self):
        """
        Crash the crash.

        Args:
            self: (todo): write your description
        """
        self.crash2('going down...')

    def crash2(self, arg):
        """
        Convert a jash argument to a c : param arg

        Args:
            self: (todo): write your description
            arg: (str): write your description
        """
        # this statement will crash on purpose:
        x = arg // 2
