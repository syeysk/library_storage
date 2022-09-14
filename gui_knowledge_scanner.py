from os import curdir, path, makedirs
from threading import Thread
from tkinter import (GROOVE, LEFT, RIGHT, TOP, Frame, LabelFrame, StringVar, Tk, W, SE, filedialog, Toplevel, VERTICAL,
    Canvas, Y, ALL, BOTH, NW, X)
from tkinter.ttk import Button, Label, Radiobutton, Separator, Notebook, Scrollbar

from gui import BasicGUI, build_scrollable_frame
from knowledge_scanner import scan_knowlege, publicate_to


class GUI(BasicGUI):
    def __init__(self):
        BasicGUI.__init__(self)

    def publicate_to(self, service_name, lables, data):
        request_data = publicate_to(service_name, data)
        #lables['id'].configure(text=request_data['id'])
        lables['url'].configure(text=request_data['url'])
        lables['publicate_datetime'].configure(text=request_data['publicate_datetime'])

    def build_publication_subcard(self, service_name, card_frame, data):
        service_data = data['publicate_to'][service_name]
        service_frame = LabelFrame(card_frame, text=service_name)
        service_frame.pack(anchor=W, fill=X)

        # frame_id = Frame(service_frame)
        # frame_id.pack(anchor=W)
        # Label(frame_id, text='ID:').pack(side=LEFT, anchor=W)
        # label_id = Label(frame_id)
        # label_id.pack(side=LEFT, anchor=W)

        frame_url = Frame(service_frame)
        frame_url.pack(anchor=W)
        Label(frame_url, text='URL:').pack(side=LEFT, anchor=W)
        label_url = Label(frame_url)
        label_url.pack(side=LEFT, anchor=W)

        frame_publicate_datetime = Frame(service_frame)
        frame_publicate_datetime.pack(anchor=W)
        Label(frame_publicate_datetime, text='Дата публикации:').pack(side=LEFT, anchor=W)
        label_publicate_datetime = Label(frame_publicate_datetime)
        label_publicate_datetime.pack(side=LEFT, anchor=W)

        labels = {
            #'id': label_id,
            'url': label_url,
            'publicate_datetime': label_publicate_datetime,
        }
        command = lambda: self.publicate_to(service_name, labels, data)
        text_of_button = None
        if service_data.get('need_publicate'):
            text_of_button = 'Опубликовать'
        elif service_data.get('need_update'):
            text_of_button = 'Обновить'

        if text_of_button:
            Button(service_frame, text=text_of_button, command=command).pack(anchor=SE)

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
                for service_name, service_data in data['publicate_to'].items():
                    self.build_publication_subcard(service_name, card_frame, data)
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
