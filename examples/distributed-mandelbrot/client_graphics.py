# mandelbrot fractal,  z=z^2+c
import time
import tkinter
from concurrent import futures
from Pyro5.api import Proxy, locate_ns


res_x = 1000
res_y = 800


class MandelWindow(object):
    def __init__(self):
        """
        Initialize the widget

        Args:
            self: (todo): write your description
        """
        self.root = tkinter.Tk()
        self.root.title("Mandelbrot (Pyro multi CPU core version)")
        canvas = tkinter.Canvas(self.root, width=res_x, height=res_y, bg="#000000")
        canvas.pack()
        self.img = tkinter.PhotoImage(width=res_x, height=res_y)
        canvas.create_image((res_x/2, res_y/2), image=self.img, state="normal")
        with locate_ns() as ns:
            mandels = ns.yplookup(meta_any={"class:mandelbrot_calc_color"})
            mandels = list(mandels.items())
        print("{0} mandelbrot calculation servers found.".format(len(mandels)))
        if not mandels:
            raise ValueError("launch at least one mandelbrot calculation server before starting this")
        self.mandels = [uri for _, (uri, meta) in mandels]
        self.pool = futures.ThreadPoolExecutor(max_workers=len(self.mandels))
        self.tasks = []
        self.start_time = time.time()
        for line in range(res_y):
            self.tasks.append(self.calc_new_line(line))
        self.root.after(100, self.draw_results)
        tkinter.mainloop()

    def draw_results(self):
        """
        Draw the results.

        Args:
            self: (todo): write your description
        """
        for task in futures.as_completed(self.tasks):
            y, pixeldata = task.result()
            self.img.put(pixeldata, (0, y))
            self.root.update()
        duration = time.time() - self.start_time
        print("Calculation took: %.2f seconds" % duration)

    def calc_new_line(self, y):
        """
        Calculate a new new server : class

        Args:
            self: (todo): write your description
            y: (todo): write your description
        """
        def line_task(server_uri, y):
            """
            Calculate the task task.

            Args:
                server_uri: (str): write your description
                y: (str): write your description
            """
            with Proxy(server_uri) as calcproxy:
                return calcproxy.calc_photoimage_line(y, res_x, res_y)
        uri = self.mandels[y % len(self.mandels)]  # round robin server selection
        return self.pool.submit(line_task, uri, y)


if __name__ == "__main__":
    window = MandelWindow()
