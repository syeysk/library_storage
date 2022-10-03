from threading import Thread
from tkinter import LEFT, RIGHT, Frame, Tk, VERTICAL, Canvas, Y, ALL, BOTH, NW
from tkinter.ttk import Scrollbar


def build_scrollable_frame(master):
    """Источник: https://www.youtube.com/watch?v=0WafQCaok6g"""
    # Crrate a main Frame
    container = Frame(master)
    # Create a Canvas to the main frame
    canvas = Canvas(container)
    canvas.pack(side=LEFT, fill=BOTH, expand=1)
    # Create a Scrollbar to the main frame
    scrollbar = Scrollbar(container, orient=VERTICAL, command=canvas.yview)
    scrollbar.pack(side=RIGHT, fill=Y)
    # Configure the Canvas
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox(ALL)))
    # Create another Frame inside the Canvas
    child = Frame(canvas)
    # Add that new Frame to a window in the Canvas
    canvas.create_window((0, 0), window=child, anchor=NW)
    return container, child


class BasicGUI(Tk):
    def __init__(self):
        Tk.__init__(self)

    def run_func_in_thread(self, func, args=(), kwargs=None, finish_func=None, finish_args=()):
        def check():
            if thread.is_alive():
                #print('поток продолжается')
                self.after(100, check)
            else:
                print('поток завершён')
                # action after finishing thread
                if finish_func:
                    finish_func(*finish_args)

        thread = Thread(None, func, args=args, kwargs=kwargs)
        thread.start()
        check()
