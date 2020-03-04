import Pyro5.api
import Pyro5.socketutil
import bench


Pyro5.api.serve({
        bench.bench: "example.benchmark"
    },
    daemon=Pyro5.api.Daemon(host=Pyro5.socketutil.get_ip_address("", True)),
    use_ns=False)
