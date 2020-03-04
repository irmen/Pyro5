from Pyro5.api import expose, serve, config


@expose
class CalcServer(object):
    def add(self, num1, num2):
        print("calling add: %d, %d" % (num1, num2))
        return num1 + num2


config.COMMTIMEOUT = 0.5  # the server should time out easily now

serve({
    CalcServer: "example.autoretry"
})
