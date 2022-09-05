from os import curdir, path, makedirs
from threading import Thread
from tkinter import GROOVE, LEFT, RIGHT, TOP, Frame, StringVar, Tk, W, filedialog
from tkinter.ttk import Button, Label, Radiobutton, Separator

from library_storage import LibraryStorage


class GUI(Tk):
    def __init__(self, lib_storage):
        Tk.__init__(self)
        self.lib_storage = lib_storage
        self.storage_db = ''
        self.storage_directory = None
        self.storage_structure = None
        self.type_scan = StringVar(value='files')

        self.storage_directory_copy = None
        self.diff_file_path = None

        self.btn_command_scan_directory = None
        self.btn_command_load_structure = None

    def progress_count_exported_files(self, number_of_current_row, count_rows, csv_current_page):
        text = '{}/{} Страниц: {}'.format(number_of_current_row, count_rows, csv_current_page)
        self.val_stat_count_exported_files.configure(text=text)

    def progress_count_scanned_files(self, total_scanned_files):
        self.val_stat_count_files.configure(text=total_scanned_files)

    def check_command_scan_files(self, thread):
        if thread.is_alive():
            self.after(1000, self.check_command_scan_files, thread)
            # print('поток выполняется')
        else:
            print('поток завершён')
            self.lib_storage.select_db(self.storage_db)

    def fg_command_scan_files(self):
        self.lib_storage.select_db(self.storage_db)
        self.lib_storage.scan_to_db(
            self.storage_directory,
            process_dublicate='original',
            progress_count_scanned_files=self.progress_count_scanned_files
        )

    def check_command_scan_structure(self, thread):
        if thread.is_alive():
            self.after(1000, self.check_command_scan_structure, thread)
            # print('поток выполняется')
        else:
            print('поток завершён')
            self.lib_storage.select_db(self.storage_db)

    def fg_command_scan_structure(self):
        self.lib_storage.select_db(self.storage_db)
        self.lib_storage.import_csv_to_db(self.storage_structure)

    def command_scan(self):
        type_scan = self.type_scan.get()
        if type_scan == 'files':
            if not self.storage_directory:
                print('Пожалуйста, выберите директорию хранилища')
                return

            thread = Thread(None, self.fg_command_scan_files)
            thread.start()
            self.check_command_scan_files(thread)
        elif type_scan == 'structure':
            if not self.storage_structure:
                print('Пожалуйста, выберите директорию хранилища')
                return

            thread = Thread(None, self.fg_command_scan_structure)
            thread.start()
            self.check_command_scan_structure(thread)

    def check_command_export(self, thread):
        if thread.is_alive():
            self.after(1000, self.check_command_export, thread)
            print('поток выполняется')
        else:
            print('поток завершён')
            self.lib_storage.select_db(self.storage_db)

    def fg_command_export(self):
        self.lib_storage.select_db(self.storage_db)
        self.lib_storage.export_db_to_csv(
            self.storage_structure,
            progress_count_exported_files=self.progress_count_exported_files
        )

    def command_export(self):
        if self.storage_structure:
            thread = Thread(None, self.fg_command_export)
            thread.start()
            self.check_command_export(thread)
        else:
            print('Пожалуйста, выберите директорию структуры')

    def select_storage(self, type_scan):
        #type_scan = self.type_scan.get()
        if type_scan == 'files':
            self.storage_directory = filedialog.askdirectory(initialdir=curdir)
            if not self.storage_directory:
                return

            self.storage_structure = '{}_structure'.format(self.storage_directory)  # '{}.zip'.format(storage_directory)
            self.storage_db = '{}.db'.format(self.storage_directory)
            if not path.exists(self.storage_structure):
                makedirs(self.storage_structure, exist_ok=True)

            self.val_storage_directory.configure(text=self.storage_directory)
        elif type_scan == 'structure':
            self.storage_directory = None
            self.storage_structure = filedialog.askdirectory(initialdir=curdir)
            if not self.storage_structure:
                return

            self.storage_db = '{}.db'.format(self.storage_structure[:-len('_structure')])

            self.val_storage_directory.configure(text='Не существует')

        self.val_stat_db_path.configure(text=self.storage_db)
        self.val_structure.configure(text=self.storage_structure)

        self.lib_storage.select_db(self.storage_db)
        total_scanned_files = self.lib_storage.db.get_count_rows()
        self.progress_count_scanned_files(total_scanned_files)

    def select_storage_directory(self):
        self.select_storage('files')

    def select_storage_structure(self):
        self.select_storage('structure')

    def select_storage_structure_copy(self):
        self.storage_directory_copy = filedialog.askdirectory(initialdir=curdir)
        if not self.storage_directory_copy:
            return

        self.val_storage_directory_copy.configure(text=self.storage_directory_copy)
        self.diff_file_path = '{}_diff.zip'.format(self.storage_directory_copy)

    def check_command_generate_diff(self, thread):
        if thread.is_alive():
            self.after(1000, self.check_command_generate_diff, thread)
            # print('поток выполняется')
        else:
            print('поток завершён')
            self.lib_storage.select_db(self.storage_db)

    def fg_command_generate_diff(self):
        self.lib_storage.select_db(self.storage_db)
        self.lib_storage.scan_to_db(
            self.storage_directory_copy,
            diff_file_path=self.diff_file_path,
            delete_dublicate=False,
            progress_count_scanned_files=None  # self.progress_count_scanned_files
        )

    def command_generate_diff(self):
        if not self.storage_directory_copy:
            print('Пожалуйста, выберите директорию копии хранилища')
            return

        thread = Thread(None, self.fg_command_generate_diff)
        thread.start()
        self.check_command_generate_diff(thread)

    def hide_btn_command_scan_directory(self):
        self.btn_command_load_structure.state(['active', '!disabled'])
        self.btn_command_scan_directory.state(['!active', 'disabled'])

    def hide_command_load_structure(self):
        self.btn_command_load_structure.state(['!active', 'disabled'])
        self.btn_command_scan_directory.state(['active', '!disabled'])

    def create_window(self):
        self.title('SYeysk LibraryStorage')

        # Оригинальное хранилище

        frame_input = Frame(self, relief=GROOVE, borderwidth=2, padx=10, pady=5)

        Label(frame_input, text='Хранилище').pack(side=TOP)

        frame_original = Frame(frame_input)
        Button(
            frame_original,
            text='Открыть директорию',
            command=self.select_storage_directory
        ).pack(side=LEFT)
        Button(
            frame_original,
            text='Открыть структуру',
            command=self.select_storage_structure
        ).pack(side=LEFT)
        frame_original.pack(side=TOP, anchor=W)

        frame_original_directory = Frame(frame_input)
        # rb_type_scan_files = Radiobutton(frame_original_directory, variable=self.type_scan, text='Директория:', value='files', command=self.hide_command_load_structure)
        # rb_type_scan_files.pack(side=LEFT)
        rb_type_scan_files = Label(frame_original_directory, text='Директория:')
        rb_type_scan_files.pack(side=LEFT)
        self.val_storage_directory = Label(frame_original_directory, text='')
        self.val_storage_directory.pack(side=LEFT)
        frame_original_directory.pack(side=TOP, anchor=W)

        frame_original_structure = Frame(frame_input)
        # rb_type_scan_structure = Radiobutton(frame_original_structure, variable=self.type_scan, text='Структура:', value='structure', command=self.hide_btn_command_scan_directory)
        # rb_type_scan_structure.pack(side=LEFT)
        rb_type_scan_structure = Label(frame_original_structure, text='Структура:')
        rb_type_scan_structure.pack(side=LEFT)
        self.val_structure = Label(frame_original_structure, text='')
        self.val_structure.pack(side=LEFT)
        frame_original_structure.pack(side=TOP, anchor=W)


        # frame_input_radios = Frame(frame_input)
        # frame_input_radios.pack(side=LEFT)

        frame_input_actions = Frame(frame_input)

        frame_input_buttons = Frame(frame_input_actions)
        self.btn_command_scan_directory = Button(frame_input_buttons, text='Сканировать директорию', command=self.command_scan)
        self.btn_command_scan_directory.pack(side=LEFT)
        # self.btn_command_load_structure = Button(frame_input_buttons, text='Загрузить структуру', command=None)
        # self.btn_command_load_structure.pack(side=LEFT)
        frame_input_buttons.pack()
        btn_command_export = Button(frame_input_buttons, text='Экспорт', command=self.command_export)
        btn_command_export.pack()

        # rb_type_scan_files.invoke()

        frame_input_actions.pack(side=LEFT)
        frame_input.pack(side=LEFT)

        # Копия хранилища

        frame_input_copy2 = Frame(self, relief=GROOVE, borderwidth=2, padx=10, pady=5)
        btn_select_storage_directory_copy = Button(
            frame_input_copy2,
            text='Открыть структуру',
            command=self.select_storage_structure_copy
        )
        btn_select_storage_directory_copy.pack()
        frame_input_copy2.pack(side=LEFT)

        separator = Separator(self, orient='horizontal')
        separator.pack()

        # Статистика

        Label(self, text='База хранилища:').pack(side=TOP)
        self.val_stat_db_path = Label(self, text='')
        self.val_stat_db_path.pack(side=TOP)

        frame_statistic = Frame(self, relief=GROOVE, borderwidth=2, padx=10, pady=5)
        lbl_stat_count_files = Label(frame_statistic, text='Файлов отсканировано:')
        lbl_stat_count_files.pack(side=TOP)
        self.val_stat_count_files = Label(frame_statistic, text='')
        self.val_stat_count_files.pack(side=TOP)
        lbl_stat_count_exported_files = Label(frame_statistic, text='Файлов экспортировано:')
        lbl_stat_count_exported_files.pack(side=TOP)
        self.val_stat_count_exported_files = Label(frame_statistic, text='')
        self.val_stat_count_exported_files.pack(side=TOP)

        frame_statistic.pack()

        # Копия хранилища

        frame_input_copy = Frame(self, relief=GROOVE, borderwidth=2, padx=10, pady=5)

        # не записывать удалённые: если это копия и мы хотим удалить из оригинпала отсутствующие в копии файлы
        frame_input_labels_copy = Frame(frame_input_copy)
        lbl_storage_directory_copy = Label(frame_input_labels_copy, text='Хранилище (копия):')
        lbl_storage_directory_copy.pack(side=LEFT)
        self.val_storage_directory_copy = Label(frame_input_labels_copy, text='')
        self.val_storage_directory_copy.pack(side=LEFT)
        frame_input_labels_copy.pack()

        frame_input_copy_buttons = Frame(frame_input_copy)
        btn_select_storage_directory = Button(
            frame_input_copy_buttons,
            text='Сгенерировать diff-файл',
            command=self.command_generate_diff
        )
        btn_select_storage_directory.pack(side=LEFT)
        # btn_command_scan = Button(frame_input_copy_buttons, text="Применить diff-файл", command=None)
        # btn_command_scan.pack(side=LEFT)
        frame_input_copy_buttons.pack(side=TOP)


        frame_input_copy.pack()



with LibraryStorage(db_path='') as lib_storage:
    gui = GUI(lib_storage)
    gui.create_window()
    gui.mainloop()
