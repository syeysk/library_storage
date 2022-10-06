from os import curdir, path, makedirs
from tkinter import (GROOVE, LEFT, TOP, Frame, LabelFrame, StringVar, W, filedialog, Toplevel, BOTH, X, Y)
from tkinter.ttk import Button, Label, Separator, Notebook

from constants_paths import DEFAULT_LIBRARY_DIRPATH
from library_storage_scanner.exporters import CSVExporter, MarkdownExporter
from library_storage_scanner.scanner import LibraryStorage
from utils_gui import BasicGUI, build_scrollable_frame


class SelectExporterWindow(BasicGUI):

    exporter_classes = {'csv': CSVExporter, 'markdown': MarkdownExporter}

    def __init__(self, parent_window):
        BasicGUI.__init__(self)

        # self.exporter_str = StringVar()
        self.parent_window = parent_window

        Label(self, text='Выберите формат сохранения:').pack(fill=Y)
        Button(
            self,
            # variable=self.exporter_str,
            text='CSV',
            # value='csv',
            command=lambda: self.set_exporter('csv'),
        ).pack(fill=Y)
        Button(
            self,
            # variable=self.exporter_str,
            text='Markdown',
            # value='markdown',
            command=lambda: self.set_exporter('markdown'),
        ).pack(fill=Y)

    def set_exporter(self, exporter_str):
        # exporter_str = self.exporter_str.get()
        # print(exporter_str, self.exporter_str)
        self.parent_window.exporter_class = self.exporter_classes[exporter_str]
        self.destroy()


class GUI(BasicGUI):
    def __init__(self, lib_storage):
        BasicGUI.__init__(self)
        self.lib_storage = lib_storage
        self.storage_db = ''
        self.storage_directory = None
        self.storage_structure = None
        self.type_scan = StringVar(value='files')

        self.storage_directory_copy = None
        self.diff_file_path = None

        self.btn_command_scan_directory = None
        self.btn_command_load_structure = None

        self.exporter_class = None

    def progress_count_exported_files(self, number_of_current_row, count_rows, csv_current_page):
        text = '{}/{} Страниц: {}'.format(number_of_current_row, count_rows, csv_current_page)
        self.val_stat_count_exported_files.configure(text=text)

    def progress_count_scanned_files(self, total_scanned_files):
        self.val_stat_count_files.configure(text=total_scanned_files)

    def fg_command_scan_files(self):
        self.lib_storage.select_db(self.storage_db)
        self.lib_storage.scan_to_db(
            self.storage_directory,
            process_dublicate='original',
            progress_count_scanned_files=self.progress_count_scanned_files,
            func_dublicate=self.add_dublicate_file_frame
        )

    def fg_command_scan_structure(self):
        self.lib_storage.select_db(self.storage_db)
        self.lib_storage.import_csv_to_db(self.storage_structure)

    def command_scan(self):
        type_scan = self.type_scan.get()
        if type_scan == 'files':
            if not self.storage_directory:
                print('Пожалуйста, выберите директорию хранилища')
                return

            window = self.create_window_scan()
            self.run_func_in_thread(
                self.fg_command_scan_files,
                finish_func=self.lib_storage.select_db,
                finish_args=(self.storage_db,),
            )
        elif type_scan == 'structure':
            if not self.storage_structure:
                print('Пожалуйста, выберите директорию хранилища')
                return

            window = self.create_window_scan()
            self.run_func_in_thread(
                self.fg_command_scan_structure,
                finish_func=self.lib_storage.select_db,
                finish_args=(self.storage_db,),
            )

    def fg_command_export(self):
        if self.exporter_class:
            self.lib_storage.select_db(self.storage_db)  # TODO: Зачем это дублируется при создании фоновой команды?
            self.lib_storage.export_db_to_csv(
                exporter=self.exporter_class(self.storage_structure),
                progress_count_exported_files=self.progress_count_exported_files
            )
            self.exporter_class = None

    def command_export(self):

        window = SelectExporterWindow(self)
        window.grab_set()
        window.focus_set()
        window.wait_window()

        if self.storage_structure:
            self.run_func_in_thread(
                self.fg_command_export,
                finish_func=self.lib_storage.select_db,
                finish_args=(self.storage_db,),
            )
        else:
            print('Пожалуйста, выберите директорию структуры')

    def set_storage(self, storage_path, type_scan):
        if type_scan == 'files':
            self.storage_directory = storage_path
            self.storage_structure = '{}_structure'.format(self.storage_directory)  # '{}.zip'.format(storage_directory)
            self.val_storage_directory.configure(text=self.storage_directory)

            self.storage_db = '{}.db'.format(self.storage_directory)
            if not path.exists(self.storage_structure):
                makedirs(self.storage_structure, exist_ok=True)
        elif type_scan == 'structure':
            self.storage_directory = None
            self.storage_structure = storage_path
            self.val_storage_directory.configure(text='Не существует')

            self.storage_db = '{}.db'.format(self.storage_structure[:-len('_structure')])

        self.val_stat_db_path.configure(text=self.storage_db)
        self.val_structure.configure(text=self.storage_structure)

        self.lib_storage.select_db(self.storage_db)
        total_scanned_files = self.lib_storage.db.get_count_rows()
        self.progress_count_scanned_files(total_scanned_files)

    def select_storage(self, type_scan):
        if type_scan == 'files':
            filepath = self.storage_directory or curdir
            storage_path = filedialog.askdirectory(initialdir=filepath)
        elif type_scan == 'structure':
            filepath = self.storage_structure or curdir
            storage_path = filedialog.askdirectory(initialdir=filepath)
        else:
            return

        if storage_path:
            self.set_storage(storage_path, type_scan)

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

        self.run_func_in_thread(
            self.fg_command_generate_diff,
            finish_func=self.lib_storage.select_db,
            finish_args=(self.storage_db,),
        )

    def hide_btn_command_scan_directory(self):
        self.btn_command_load_structure.state(['active', '!disabled'])
        self.btn_command_scan_directory.state(['!active', 'disabled'])

    def hide_command_load_structure(self):
        self.btn_command_load_structure.state(['!active', 'disabled'])
        self.btn_command_scan_directory.state(['active', '!disabled'])

    def add_dublicate_file_frame(self, existed_filepath, inserted_filepath):
        frame = Frame(self.frame_dublicates, relief=GROOVE, borderwidth=2, padx=10, pady=5)
        frame.pack(fill=X)

        frame1 = Frame(frame)
        frame1.pack(anchor=W)
        button1 = Button(frame1, text='Удалить')
        button1.pack(side=LEFT)
        existed_label = Label(frame1, text=existed_filepath)
        existed_label.pack(side=LEFT)

        frame2 = Frame(frame)
        frame2.pack(anchor=W)
        button2 = Button(frame2, text='Удалить')
        button2.pack(side=LEFT)
        inserted_label = Label(frame2, text=inserted_filepath)
        inserted_label.pack(side=LEFT)

    def create_window_scan(self):
        window_scan = Toplevel(self)
        notebook = Notebook(window_scan)
        notebook.pack(fill=BOTH, expand=1)

        container_dublicates, self.frame_dublicates = build_scrollable_frame(notebook)
        container_info, self.frame_info = build_scrollable_frame(notebook)

        # for i in range(30):
        #     Label(self.frame_dublicates, text=f'line {i}').pack()

        for i in range(20):
            Label(self.frame_info, text=f'line {i}').pack()

        notebook.add(container_dublicates, text='Дубликаты')
        notebook.add(container_info, text='Прочее')

        return window_scan

    def create_window(self):
        self.title('SYeysk LibraryStorage')

        # Оригинальное хранилище

        frame_inputs = Frame(self)

        frame_input = LabelFrame(frame_inputs, text='Хранилище оригинальное', relief=GROOVE, borderwidth=2, padx=10, pady=5)

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
        self.btn_command_scan_directory = Button(
            frame_input_buttons,
            text='Сканировать директорию',
            command=self.command_scan
        )
        self.btn_command_scan_directory.pack(side=LEFT)
        # self.btn_command_load_structure = Button(frame_input_buttons, text='Загрузить структуру', command=None)
        # self.btn_command_load_structure.pack(side=LEFT)
        frame_input_buttons.pack()
        btn_command_export = Button(frame_input_buttons, text='Экспорт', command=self.command_export)
        btn_command_export.pack()

        # rb_type_scan_files.invoke()

        frame_input_actions.pack(side=LEFT)
        frame_input.pack(side=LEFT, padx=5, pady=5)

        # Копия хранилища

        frame_input_copy2 = LabelFrame(frame_inputs, text='Хранилище - копия', relief=GROOVE, borderwidth=2, padx=10, pady=5)
        btn_select_storage_directory_copy = Button(
            frame_input_copy2,
            text='Открыть структуру',
            command=self.select_storage_structure_copy
        )
        btn_select_storage_directory_copy.pack()
        frame_input_copy2.pack(side=LEFT)

        separator = Separator(self, orient='horizontal')
        separator.pack()
        
        frame_inputs.pack(padx=5, pady=5)

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

        self.set_storage(DEFAULT_LIBRARY_DIRPATH, 'files')


if __name__ == '__main__':
    with LibraryStorage() as lib_storage:
        gui = GUI(lib_storage)
        gui.create_window()
        gui.mainloop()
