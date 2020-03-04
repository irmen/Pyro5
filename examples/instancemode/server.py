from Pyro5.api import expose, behavior, serve, current_context


@behavior(instance_mode="single")
class SingleInstance(object):
    @expose
    def msg(self, message):
        print("[%s] %s.msg: %s" % (id(self), self.__class__.__name__, message))
        return id(self)


@behavior(instance_mode="session", instance_creator=lambda clazz: clazz.create_instance())
class SessionInstance(object):
    @expose
    def msg(self, message):
        print("[%s] %s.msg: %s" % (id(self), self.__class__.__name__, message))
        return id(self), self.correlation_id
    @classmethod
    def create_instance(cls):
        obj = cls()
        obj.correlation_id = current_context.correlation_id
        return obj


@behavior(instance_mode="percall")
class PercallInstance(object):
    @expose
    def msg(self, message):
        print("[%s] %s.msg: %s" % (id(self), self.__class__.__name__, message))
        return id(self)


if __name__ == "__main__":
    # please make sure a name server is running somewhere first.
    serve({
        SingleInstance: "instance.single",
        SessionInstance: "instance.session",
        PercallInstance: "instance.percall"
    }, verbose=True)
