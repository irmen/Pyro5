# ascii animation of zooming a mandelbrot fractal,  z=z^2+c
import os
import time
import threading
import platform
from Pyro5.api import locate_ns, Proxy, BatchProxy


class MandelZoomer(object):
    res_x = 100
    res_y = 40

    def __init__(self):
        self.num_lines_lock = threading.Lock()
        self.num_lines_ready = 0
        self.all_lines_ready = threading.Event()
        self.result = []
        with locate_ns() as ns:
            mandels = ns.yplookup(meta_any={"class:mandelbrot_calc"})
            mandels = list(mandels.items())
        print("{0} mandelbrot calculation servers found.".format(len(mandels)))
        if not mandels:
            raise ValueError("launch at least one mandelbrot calculation server before starting this")
        time.sleep(2)
        self.mandels = [Proxy(uri) for _, (uri, meta) in mandels]

    def batch_result(self, results):
        num_result_lines = 0
        for linenr, line in results:
            self.result[linenr] = line
            num_result_lines += 1
        with self.num_lines_lock:
            self.num_lines_ready += num_result_lines
            if self.num_lines_ready >= self.res_y:
                self.all_lines_ready.set()

    def screen(self, start, width):
        dr = width / self.res_x
        di = dr*(self.res_x/self.res_y)
        di *= 0.8   # aspect ratio correction
        self.num_lines_ready = 0
        self.all_lines_ready.clear()
        self.result = ["?"] * self.res_y
        servers = [BatchProxy(proxy) for proxy in self.mandels]
        for i in range(self.res_y):
            server = servers[i % len(servers)]
            server.calc_line(start, self.res_x, i*di, dr, i)
        for batch in servers:
            results = batch() # @todo the batched calls in the client are processed sequentially because Pyro5 no longer has async proxies itself - FIX THIS
            self.batch_result(results)
        self.all_lines_ready.wait(timeout=5)
        return "\n".join(self.result)

    def cls(self):
        if platform.platform().startswith("Windows"):
            os.system("cls")
        else:
            print(chr(27)+"[2J"+chr(27)+"[1;1H", end="")  # ansi clear screen


if __name__ == "__main__":
    start = -2.0-1.0j
    width = 3.0
    duration = 30.0
    wallclock_start = time.time()
    frames = 0
    zoomer = MandelZoomer()
    zoomer.cls()
    print("This is a mandelbrot zoom animation running using Pyro, it will use all calculation server processes that are available.")
    while True:
        time_passed = time.time() - wallclock_start
        if time_passed >= duration:
            break
        actual_width = width * (1-time_passed/duration/1.1)
        actual_start = start + (0.06-0.002j)*time_passed
        frame = zoomer.screen(actual_start, actual_width)
        zoomer.cls()
        fps = frames/time_passed if time_passed > 0 else 0
        print("%.1f FPS time=%.2f width=%.2f" % (fps, time_passed, actual_width))
        print(frame)
        frames += 1
    print("Final FPS: %.2f" % fps)

