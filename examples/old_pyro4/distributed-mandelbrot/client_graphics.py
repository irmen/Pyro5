# mandelbrot fractal,  z=z^2+c
import time
import threading
from queue import Queue, Empty
import tkinter
from Pyro5.compatibility import Pyro4
import Pyro4


res_x = 1000
res_y = 800


class MandelWindow(object):
    def __init__(self):
        self.root = tkinter.Tk()
        self.root.title("Mandelbrot (Pyro multi CPU core version)")
        canvas = tkinter.Canvas(self.root, width=res_x, height=res_y, bg="#000000")
        canvas.pack()
        self.img = tkinter.PhotoImage(width=res_x, height=res_y)
        canvas.create_image((res_x/2, res_y/2), image=self.img, state="normal")
        with Pyro4.locateNS() as ns:
            mandels = ns.yplookup(meta_any={"class:mandelbrot_calc_color"})
            mandels = list(mandels.items())
        print("{0} mandelbrot calculation servers found.".format(len(mandels)))
        if not mandels:
            raise ValueError("launch at least one mandelbrot calculation server before starting this")
        self.mandels = [Pyro4.Proxy(uri) for _, (uri, meta) in mandels]
        #for m in self.mandels:
        #    m._pyroAsync()   # set them to asynchronous mode
        # @todo the calls in the client are processed sequentially because Pyro5 no longer has async proxies itself - FIX THIS
        for proxy in self.mandels:
            proxy._pyroBind()
        self.lines = list(reversed(range(res_y)))
        self.draw_data = Queue()
        self.root.after(1000, self.draw_lines)
        tkinter.mainloop()

    def draw_lines(self):
        # start by putting each of the found servers to work on a single line,
        # the other lines will be done in turn when the results come back.
        for _ in range(len(self.mandels)):
            self.calc_new_line()
        self.start_time = time.time()
        self.draw_results()

    def draw_results(self):
        # we do the drawing of the results in the gui main thread
        # otherwise strange things may happen such as freezes
        try:
            while True:
                y, pixeldata = self.draw_data.get(block=False)
                if pixeldata:
                    self.img.put(pixeldata, (0, y))
                else:
                    # end reached
                    duration = time.time() - self.start_time
                    print("Calculation took: %.2f seconds" % duration)
                    break
        except Empty:
            self.root.after(100, self.draw_results)

    def calc_new_line(self):
        y = self.lines.pop()
        server = self.mandels[y % len(self.mandels)]  # round robin server selection
        # @todo the calls in the client are processed sequentially because Pyro5 no longer has async proxies itself - FIX THIS
        def calc_in_thread():
            with Pyro4.Proxy(server._pyroUri) as calcproxy:
                result = calcproxy.calc_photoimage_line(y, res_x, res_y)
                self.process_result(result)
                # self.root.after(5, lambda result=result: self.process_result(result))
        threading.Thread(target=calc_in_thread).start()

    def process_result(self, result):
        self.draw_data.put(result)  # drawing should be done by the main gui thread
        if self.lines:
            self.calc_new_line()
        else:
            self.draw_data.put((None, None))  # end-sentinel


if __name__ == "__main__":
    window = MandelWindow()
