from Pyro5.api import expose, serve, config


@expose
class CalcServer(object):
    def add(self, num1, num2):
        """
        Add num1 num2

        Args:
            self: (todo): write your description
            num1: (int): write your description
            num2: (int): write your description
        """
        print("calling add: %d, %d" % (num1, num2))
        return num1 + num2


config.COMMTIMEOUT = 0.5  # the server should time out easily now

serve({
    CalcServer: "example.autoretry"
})
