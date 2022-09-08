from os import curdir, path, makedirs
from threading import Thread
from tkinter import (GROOVE, LEFT, RIGHT, TOP, Frame, LabelFrame, StringVar, Tk, W, filedialog, Toplevel, VERTICAL,
    Canvas, Y, ALL, BOTH, NW, X)
from tkinter.ttk import Button, Label, Radiobutton, Separator, Notebook, Scrollbar

from gui import BasicGUI, build_scrollable_frame
from knowledge_scanner import scan_knowlege


class GUI(BasicGUI):
    def __init__(self):
        BasicGUI.__init__(self)

    def scan_knowledge(self):
        def print_url(url):
            Label(self.frame_url, text=url).pack(anchor=W)

        self.run_func_in_thread(lambda: scan_knowlege(print_url=print_url))

    def create_window(self):
        self.title('SYeysk Knowledge Scanner')

        frame_buttons = Frame(self)
        frame_buttons.pack(fill=X)

        Button(
            frame_buttons,
            text='Запустить сканирование',
            command=self.scan_knowledge
        ).pack(side=LEFT)

        notebook = Notebook(self)
        notebook.pack(fill=BOTH, expand=1)

        container_publication, self.frame_publication = build_scrollable_frame(notebook)
        container_extension, self.frame_extension = build_scrollable_frame(notebook)
        container_url, self.frame_url = build_scrollable_frame(notebook)

        notebook.add(container_publication, text='Публикации')
        notebook.add(container_extension, text='Расширение')
        notebook.add(container_url, text='URL')


if __name__ == '__main__':
    gui = GUI()
    gui.create_window()
    gui.mainloop()
