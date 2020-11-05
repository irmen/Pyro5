# mandelbrot fractal,  z=z^2+c
import time
import tkinter
from server import MandelbrotColorPixels


res_x = 1000
res_y = 800


class MandelWindow(object):
    def __init__(self):
        """
        Initialize widget

        Args:
            self: (todo): write your description
        """
        self.root = tkinter.Tk()
        self.root.title("Mandelbrot (Single CPU core)")
        canvas = tkinter.Canvas(self.root, width=res_x, height=res_y, bg="#000000")
        canvas.pack()
        self.img = tkinter.PhotoImage(width=res_x, height=res_y)
        canvas.create_image((res_x/2, res_y/2), image=self.img, state="normal")
        self.mandel = MandelbrotColorPixels()
        self.start_time = time.time()
        self.root.after(1000, lambda: self.draw_line(0))
        tkinter.mainloop()

    def draw_line(self, y):
        """
        Draw a line

        Args:
            self: (todo): write your description
            y: (int): write your description
        """
        _, pixeldata = self.mandel.calc_photoimage_line(y, res_x, res_y)
        self.img.put(pixeldata, (0, y))
        if y < res_y:
            self.root.after_idle(lambda: self.draw_line(y+1))
        else:
            duration = time.time() - self.start_time
            print("Calculation took: %.2f seconds" % duration)


if __name__ == "__main__":
    window = MandelWindow()
