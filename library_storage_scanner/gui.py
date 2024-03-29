from os import curdir, remove
from os.path import basename, dirname
from tkinter import (GROOVE, LEFT, TOP, Frame, LabelFrame, StringVar, IntVar, W, filedialog, Toplevel, BOTH, X, Y)
from tkinter.ttk import Button, Label, Separator, Notebook

from constants import DEFAULT_LIBRARY_DIRPATH, DEFAULT_LIBRARY_STRUCTURE_DIRPATH
from library_storage_scanner.exporters import CSVExporter, MarkdownExporter
from library_storage_scanner.scanner import DBStorage, LibraryStorage
from utils_gui import BasicGUI, build_scrollable_frame


class SelectExporterWindow(BasicGUI):
    exporter_classes = {'csv': CSVExporter, 'markdown': MarkdownExporter}

    def __init__(self, data_for_update, storage_structure, auto_storage_structure):
        BasicGUI.__init__(self)
        self.data_for_update = data_for_update
        self.auto_storage_structure = auto_storage_structure
        self.data_for_update['storage_structure'] = storage_structure

        frame_structure = LabelFrame(self, text='Куда экспортировать')
        self.label_structure = Label(frame_structure, text=storage_structure)
        self.label_structure.pack(fill=X)
        frame_structure_buttons = Frame(frame_structure)
        Button(
            frame_structure_buttons,
            text='Автоматически',
            command=self.set_path_auto,
        ).pack(side=LEFT)
        Button(
            frame_structure_buttons,
            text='Выбрать вручную',
            command=self.set_path_handly,
        ).pack(side=LEFT)
        frame_structure_buttons.pack()

        frame_structure.pack(fill=X)

        frame_format = LabelFrame(self, text='Формат сохранения (нажмите для экспорта)')

        Button(
            frame_format,
            text='CSV',
            command=lambda: self.set_exporter('csv'),
        ).pack(side=LEFT)
        Button(
            frame_format,
            text='Markdown',
            command=lambda: self.set_exporter('markdown'),
        ).pack(side=LEFT)
        frame_format.pack(fill=X)

    def set_path_auto(self):
        self.data_for_update['storage_structure'] = self.auto_storage_structure
        self.label_structure.configure(text=self.data_for_update['storage_structure'])

    def set_path_handly(self):
        storage_structure = filedialog.askdirectory(master=self, initialdir=self.data_for_update['storage_structure'])
        if storage_structure:
            self.data_for_update['storage_structure'] = storage_structure
            self.label_structure.configure(text=self.data_for_update['storage_structure'])

    def set_exporter(self, exporter_str):
        self.data_for_update['exporter_class'] = self.exporter_classes[exporter_str]
        self.destroy()


class ScanWindow:
    def __init__(self, parent_window, type_scan, lib_storage, storage_path):
        scan_window = Toplevel(parent_window)
        scan_window.overrideredirect = True
        self.parent_window = parent_window

        notebook = Notebook(scan_window)
        notebook.pack(fill=BOTH, expand=1)

        container_dublicates, self.frame_dublicates = build_scrollable_frame(notebook)
        container_info, self.frame_info = build_scrollable_frame(notebook)

        notebook.add(container_dublicates, text='Дубликаты')
        notebook.add(container_info, text='Прочее')

        self.lib_storage = lib_storage
        self.storage_path = storage_path
        self.type_scan = type_scan
        self.dublicate_frames = {}

    def run(self):
        self.lib_storage.db.reopen()
        if self.type_scan == 'files':
            self.command_scan_files()
        if self.type_scan == 'structure':
            self.command_scan_structure()

    @staticmethod
    def build_button_delete_dublicate_file(master, viewed_filepath, command):
        frame = Frame(master)
        frame.pack(anchor=W)
        button = Button(frame, text='Удалить')
        button.configure(command=lambda: command(button.winfo_id()))
        button.pack(side=LEFT)
        Label(frame, text=viewed_filepath).pack(side=LEFT)
        return button

    def add_dublicate_file_frame(self, existed_filepath, inserted_filepath, file_hash):
        def delete_file(winfo_id):
            button = self.dublicate_frames[file_hash]['buttons'][winfo_id]
            if winfo_id == self.dublicate_frames[file_hash]['button_existed']:
                filepath = self.lib_storage.db.get_filepath(file_hash)
                del self.dublicate_frames[file_hash]['buttons'][winfo_id]
                del self.dublicate_frames[file_hash]['paths'][winfo_id]
                new_winfo_id = list(self.dublicate_frames[file_hash]['buttons'].keys())[0]
                new_filepath = self.dublicate_frames[file_hash]['paths'][new_winfo_id]
                self.dublicate_frames[file_hash]['button_existed'] = new_winfo_id
                self.lib_storage.db.update(file_hash, dirname(new_filepath), basename(new_filepath))
            else:
                filepath = self.dublicate_frames[file_hash]['paths'][winfo_id]
                del self.dublicate_frames[file_hash]['buttons'][winfo_id]
                del self.dublicate_frames[file_hash]['paths'][winfo_id]

            remove(filepath)
            button.state(['!active', 'disabled'])
            button.configure(text='удалён')

            if len(self.dublicate_frames[file_hash]['buttons']) == 1:
                single_winfo_id, single_button = list(self.dublicate_frames[file_hash]['buttons'].items())[0]
                single_button.state(['!active', 'disabled'])
                single_button.configure(text='единственный')

        double_dict = self.dublicate_frames.setdefault(file_hash, {})
        if not double_dict:
            frame = LabelFrame(self.frame_dublicates, text=file_hash, relief=GROOVE, borderwidth=2, padx=10, pady=5)
            frame.pack(fill=X)
            button = self.build_button_delete_dublicate_file(frame, existed_filepath, delete_file)
            double_dict['button_existed'] = button.winfo_id()
            double_dict['frame'] = frame
            double_dict['buttons'] = {button.winfo_id(): button}
            double_dict['paths'] = {button.winfo_id(): existed_filepath}

        button = self.build_button_delete_dublicate_file(double_dict['frame'], inserted_filepath, delete_file)
        double_dict['buttons'][button.winfo_id()] = button
        double_dict['paths'][button.winfo_id()] = inserted_filepath

    def progress_count_scanned_files(self, total_scanned_files):
        self.parent_window.variable_count_scanned_files.set(total_scanned_files)

    def command_scan_files(self):
        self.lib_storage.scan_to_db(
            self.storage_path,
            process_dublicate='original',
            progress_count_scanned_files=self.progress_count_scanned_files,
            func_dublicate=self.add_dublicate_file_frame
        )

    def command_scan_structure(self):
        self.lib_storage.import_csv_to_db(self.storage_path)


class GUI(BasicGUI):
    def __init__(self, lib_storage):
        BasicGUI.__init__(self)
        self.lib_storage = lib_storage
        self.storage_directory = None
        self.storage_structure = None
        self.type_scan = StringVar(value='files')

        self.storage_directory_copy = None
        self.diff_file_path = None

        self.btn_command_scan_directory = None
        self.btn_command_load_structure = None

        self.variable_count_scanned_files = IntVar(value=0)

    def progress_count_exported_files(self, number_of_current_row, count_rows, csv_current_page):
        text = '{}/{} Страниц: {}'.format(number_of_current_row, count_rows, csv_current_page)
        self.val_stat_count_exported_files.configure(text=text)

    def command_scan(self):
        type_scan = self.type_scan.get()
        if type_scan == 'files':
            storage_path = self.storage_directory
            if not self.storage_directory:
                print('Пожалуйста, выберите директорию хранилища')
                return

        elif type_scan == 'structure':
            storage_path = self.storage_structure
            if not self.storage_structure:
                print('Пожалуйста, выберите директорию хранилища')
                return

        window = ScanWindow(self, type_scan, self.lib_storage, storage_path)
        self.run_func_in_thread(window.run, finish_func=self.lib_storage.db.reopen)
        # self.lib_storage.db.reopen()

    def fg_command_export(self, exporter_class):
        if exporter_class:
            self.lib_storage.db.reopen()
            self.lib_storage.export_db_to_csv(
                exporter=exporter_class(self.storage_structure, self.storage_directory),
                progress_count_exported_files=self.progress_count_exported_files
            )

    def command_export(self):
        data_for_update = {}
        window = SelectExporterWindow(
            data_for_update,
            self.storage_structure,
            '{}_structure'.format(self.storage_directory),
        )
        window.grab_set()
        window.focus_set()
        window.wait_window()

        storage_structure = data_for_update.get('storage_structure')
        exporter_class = data_for_update.get('exporter_class')

        if exporter_class:
            self.storage_structure = storage_structure
            self.val_structure.configure(text=self.storage_structure)
            self.run_func_in_thread(
                self.fg_command_export,
                args=(exporter_class,),
                finish_func=self.lib_storage.db.reopen,
            )

    def set_storage(self, storage_path, type_scan):
        if type_scan == 'files':
            self.storage_directory = storage_path
            self.storage_structure = '{}_structure'.format(self.storage_directory)  # '{}.zip'.format(storage_directory)
            self.val_storage_directory.configure(text=self.storage_directory)
            storage_db = '{}.db'.format(self.storage_directory)
            self.btn_command_export.state(['active', '!disabled'])
        elif type_scan == 'structure':
            self.storage_directory = None
            self.storage_structure = storage_path
            self.val_storage_directory.configure(text='Не существует')
            storage_db = '{}.db'.format(self.storage_structure[:-len('_structure')])
            self.btn_command_export.state(['!active', 'disabled'])
        else:
            return

        self.val_stat_db_path.configure(text=storage_db)
        self.val_structure.configure(text=self.storage_structure)

        self.lib_storage.set_db(DBStorage(storage_db))
        total_scanned_files = self.lib_storage.db.get_count_rows()
        self.variable_count_scanned_files.set(total_scanned_files)

    def select_storage(self, type_scan):
        storage_path = None
        if type_scan == 'files':
            storage_path = filedialog.askdirectory(initialdir=self.storage_directory or curdir)
        elif type_scan == 'structure':
            storage_path = filedialog.askdirectory(initialdir=self.storage_structure or curdir)

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
        # self.lib_storage.db.reopen()
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
            # finish_func=self.lib_storage.db.reopen,
        )

    def create_window(self):
        self.title('SYeysk LibraryStorage')

        # Оригинальное хранилище

        frame_inputs = Frame(self)

        frame_input = LabelFrame(
            frame_inputs,
            text='Хранилище оригинальное',
            relief=GROOVE,
            borderwidth=2,
            padx=10,
            pady=5,
        )

        frame_original = Frame(frame_input)
        Button(frame_original, text='Открыть хранилище', command=self.select_storage_directory).pack(side=LEFT)
        Button(frame_original, text='Открыть структуру', command=self.select_storage_structure).pack(side=LEFT)
        frame_original.pack(side=TOP, anchor=W)

        frame_original_directory = Frame(frame_input)
        Label(frame_original_directory, text='Хранилище:').pack(side=LEFT)
        self.val_storage_directory = Label(frame_original_directory, text='')
        self.val_storage_directory.pack(side=LEFT)
        frame_original_directory.pack(side=TOP, anchor=W)

        frame_original_structure = Frame(frame_input)
        Label(frame_original_structure, text='Структура:').pack(side=LEFT)
        self.val_structure = Label(frame_original_structure, text='')
        self.val_structure.pack(side=LEFT)
        frame_original_structure.pack(side=TOP, anchor=W)

        frame_original_db = Frame(frame_input)
        Label(frame_original_db, text='База данных:').pack(side=LEFT)
        self.val_stat_db_path = Label(frame_original_db, text='')
        self.val_stat_db_path.pack(side=TOP)
        frame_original_db.pack(side=TOP, anchor=W)

        frame_input_actions = Frame(frame_input)

        frame_input_buttons = Frame(frame_input_actions)
        self.btn_command_scan_directory = Button(frame_input_buttons, text='Сканировать', command=self.command_scan)
        self.btn_command_scan_directory.pack(side=LEFT)
        frame_input_buttons.pack()
        self.btn_command_export = Button(frame_input_buttons, text='Экспорт', command=self.command_export)
        self.btn_command_export.pack()

        frame_input_actions.pack(side=LEFT)
        frame_input.pack(side=LEFT, padx=5, pady=5)

        # Копия хранилища

        frame_input_copy2 = LabelFrame(
            frame_inputs,
            text='Хранилище - копия',
            relief=GROOVE,
            borderwidth=2,
            padx=10,
            pady=5,
        )
        btn_select_storage_directory_copy = Button(
            frame_input_copy2,
            text='Открыть структуру',
            command=self.select_storage_structure_copy,
        )
        btn_select_storage_directory_copy.pack()
        frame_input_copy2.pack(side=LEFT)

        separator = Separator(self, orient='horizontal')
        separator.pack()

        frame_inputs.pack(padx=5, pady=5)

        # Статистика

        frame_statistic = Frame(self, relief=GROOVE, borderwidth=2, padx=10, pady=5)
        lbl_stat_count_files = Label(frame_statistic, text='Файлов отсканировано:')
        lbl_stat_count_files.pack(side=TOP)
        self.val_stat_count_files = Label(frame_statistic, textvariable=self.variable_count_scanned_files)
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
        if DEFAULT_LIBRARY_STRUCTURE_DIRPATH:
            self.storage_structure = DEFAULT_LIBRARY_STRUCTURE_DIRPATH
            self.val_structure.configure(text=DEFAULT_LIBRARY_STRUCTURE_DIRPATH)


if __name__ == '__main__':
    with LibraryStorage() as lib_storage:
        gui = GUI(lib_storage)
        gui.create_window()
        gui.mainloop()
