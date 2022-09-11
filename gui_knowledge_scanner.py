from os import curdir, path, makedirs
from threading import Thread
from tkinter import (GROOVE, LEFT, RIGHT, TOP, Frame, LabelFrame, StringVar, Tk, W, SE, filedialog, Toplevel, VERTICAL,
    Canvas, Y, ALL, BOTH, NW, X)
from tkinter.ttk import Button, Label, Radiobutton, Separator, Notebook, Scrollbar

from gui import BasicGUI, build_scrollable_frame
from knowledge_scanner import scan_knowlege


class GUI(BasicGUI):
    def __init__(self):
        BasicGUI.__init__(self)

    def scan_knowledge(self):
        def logger_action(name, data):
            def build_action_card(master2):
                card_frame = Frame(master2, relief=GROOVE, borderwidth=2)
                card_frame.pack(anchor=W, pady=5, padx=10, fill=X)
                Label(card_frame, text=data['relative_filepath'], background='gray').pack(anchor=W, fill=X)
                return card_frame

            if name == 'found_url':
                card_frame = build_action_card(self.frame_url)
                Label(card_frame, text=data['url']).pack(anchor=W)
            elif name == 'publicate_to':
                card_frame = build_action_card(self.frame_publication)
                Label(card_frame, text=data['title']).pack(anchor=W, fill=X)
                for service_name, service_status in data['publicate_to'].items():
                    service_frame = LabelFrame(card_frame, text=service_name)
                    service_frame.pack(anchor=W, fill=X)
                    Button(service_frame, text='Опубликовать').pack(anchor=SE)
            else:
                card_frame = build_action_card(self.frame_other)
                if name == 'invalid_extension':
                    Label(card_frame, text='Некорректное расширение файла').pack(anchor=W)
                elif name == 'unfound_yaml_key':
                    Label(card_frame, text='Некорректный мета-ключ: {}'.format(data['key'])).pack(anchor=W)
                elif name == 'unfound_title':
                    Label(card_frame, text='Не найден заголовок').pack(anchor=W)
                else:
                    print(name, data)

        self.run_func_in_thread(lambda: scan_knowlege(logger_action=logger_action))

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
        container_other, self.frame_other = build_scrollable_frame(notebook)
        container_url, self.frame_url = build_scrollable_frame(notebook)

        notebook.add(container_publication, text='Публикации')
        notebook.add(container_other, text='Прочее')
        notebook.add(container_url, text='URL')


if __name__ == '__main__':
    gui = GUI()
    gui.create_window()
    gui.mainloop()
