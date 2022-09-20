from os import curdir, path, makedirs
from threading import Thread
from tkinter import (GROOVE, LEFT, RIGHT, TOP, Frame, LabelFrame, StringVar, Tk, W, SE, filedialog, Toplevel, VERTICAL,
    Canvas, Y, ALL, BOTH, NW, X, Entry, Text)
from tkinter.ttk import Button, Label, Radiobutton, Separator, Notebook, Scrollbar

from gui import BasicGUI, build_scrollable_frame
from knowledge_scanner import DEFAULT_PASSWORD_FILEPATH, DEFAULT_NOTES_DIRPATH, scan_knowlege


class GUI(BasicGUI):
    def __init__(self):
        BasicGUI.__init__(self)
        self.password_filepath = DEFAULT_PASSWORD_FILEPATH
        self.notes_dirpath = DEFAULT_NOTES_DIRPATH
        self.password = None
        self.var_password = StringVar(value='')

    def save(self, service_name, note):
        note.save()
        custom_data = note.custom[service_name]
        custom_data['button_save'].state(['!active', 'disabled'])

    def publicate_to(self, service_name, note):
        custom_data = note.custom[service_name]
        service_data = note.publicate(service_name, self.password_filepath, self.password)
        error = service_data.get('error')
        if error:
            print('Error:', error)
        else:
            #lables['id'].configure(text=service_data['id'])
            custom_data['label_url'].configure(text=service_data['url'])
            custom_data['label_publicate_datetime'].configure(text=service_data['publicate_datetime'])
            custom_data['button_save'].state(['active', '!disabled'])
            custom_data['button_publicate'].state(['!active', 'disabled'])

    def build_publication_subcard(self, service_name, card_frame, note):
        service_data = note.meta['publicate_to'][service_name]
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
        label_url = Label(frame_url, text=service_data.get('url', ''))
        label_url.pack(side=LEFT, anchor=W)

        frame_publicate_datetime = Frame(service_frame)
        frame_publicate_datetime.pack(anchor=W)
        Label(frame_publicate_datetime, text='Дата публикации:').pack(side=LEFT, anchor=W)
        label_publicate_datetime = Label(frame_publicate_datetime, text=service_data.get('publicate_datetime', ''))
        label_publicate_datetime.pack(side=LEFT, anchor=W)

        custom_data = note.custom.setdefault(service_name, {})
        custom_data['label_url'] = label_url
        custom_data['label_publicate_datetime'] = label_publicate_datetime
        text_of_button = None
        if note.need_create_publication(service_name) == 'create':
            text_of_button = 'Опубликовать'
        elif note.need_create_publication(service_name) == 'update':
            text_of_button = 'Обновить'

        if text_of_button:
            frame_buttons = Frame(service_frame)
            frame_buttons.pack(fill=X)

            # TODO: кнопка должна сохранять данные только конкретного сервиса, храня его отдельно и при сохранении добавляя к обще метаинформации
            button_save = Button(frame_buttons, text='Сохранить', command=lambda: self.save(service_name, note))
            button_save.pack(side=RIGHT, anchor=SE)
            button_save.state(['!active', 'disabled'])
            custom_data['button_save'] = button_save

            button_publicate = Button(
                frame_buttons,
                text=text_of_button,
                command=lambda: self.publicate_to(service_name, note)
            )
            button_publicate.pack(side=RIGHT, anchor=SE)
            custom_data['button_publicate'] = button_publicate

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
                note = data['note']
                Label(card_frame, text=note.title).pack(anchor=W, fill=X)
                for service_name, service_data in note.meta['publicate_to'].items():
                    self.build_publication_subcard(service_name, card_frame, note)
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

        self.run_func_in_thread(lambda: scan_knowlege(logger_action, self.notes_dirpath))

    def select_notes_dirpath(self):
        notes_dirpath = filedialog.askdirectory(initialdir=self.notes_dirpath)
        if not notes_dirpath:
            return

        self.notes_dirpath = notes_dirpath
        self.label_storage.configure(text=self.notes_dirpath)

    def select_password_filepath(self):
        password_filepath = filedialog.askopenfile(initialdir=path.dirname(self.password_filepath))
        if not password_filepath:
            return

        self.password_filepath = password_filepath
        self.label_passwords.configure(text=self.password_filepath)

    def window_set_password(self):
        def set_password():
            self.password = self.var_password.get()
            window.destroy()

        window = Toplevel(self)
        frame_field = Frame(window)
        frame_field.pack(fill=X)
        Label(frame_field, text='Пароль:').pack(side=LEFT)
        entry_password = Entry(frame_field, textvariable=self.var_password)
        entry_password.pack(side=LEFT)
        entry_password.focus()

        frame_button = Frame(window)
        frame_button.pack(fill=X)
        Button(frame_button, text='Сохранить', command=set_password).pack(side=LEFT)

    def create_window(self):
        self.title('SYeysk Knowledge Scanner')

        frame_storage = Frame(self)
        Button(frame_storage, text='Изменить', command=self.select_notes_dirpath).pack(side=LEFT)
        Label(frame_storage, text='Каталог заметок:').pack(side=LEFT)
        self.label_storage = Label(frame_storage, text=self.notes_dirpath)
        self.label_storage.pack(side=LEFT)
        frame_storage.pack(fill=X)

        frame_password = Frame(self)
        Button(frame_password, text='Изменить', command=self.select_password_filepath).pack(side=LEFT)
        Button(frame_password, text='Пароль', command=self.window_set_password).pack(side=LEFT)
        Label(frame_password, text='Хранилище паролей:').pack(side=LEFT)
        self.label_passwords = Label(frame_password, text=self.password_filepath)
        self.label_passwords.pack(side=LEFT)
        frame_password.pack(fill=X)

        frame_buttons = Frame(self)
        frame_buttons.pack(fill=X)

        Button(
            frame_buttons,
            text='Запустить сканирование',
            command=self.scan_knowledge
        ).pack(side=RIGHT)

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
