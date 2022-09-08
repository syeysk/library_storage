from os import curdir, path, makedirs
from threading import Thread
from tkinter import (GROOVE, LEFT, RIGHT, TOP, Frame, LabelFrame, StringVar, Tk, W, filedialog, Toplevel, VERTICAL,
    Canvas, Y, ALL, BOTH, NW, X)
from tkinter.ttk import Button, Label, Radiobutton, Separator, Notebook, Scrollbar

from library_storage import LibraryStorage


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

    def run_func_in_thread(self, func, finish_func=None):
        def check():
            if thread.is_alive():
                print('поток продолжается')
                self.after(1000, check)
            else:
                print('поток завершён')
                # action after finishing thread
                if finish_func:
                    finish_func()

        thread = Thread(None, func)
        thread.start()
        check()


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
            self.run_func_in_thread(self.fg_command_scan_files, lambda: self.lib_storage.select_db(self.storage_db))
        elif type_scan == 'structure':
            if not self.storage_structure:
                print('Пожалуйста, выберите директорию хранилища')
                return

            window = self.create_window_scan()
            self.run_func_in_thread(self.fg_command_scan_structure, lambda: self.lib_storage.select_db(self.storage_db))

    def fg_command_export(self):
        self.lib_storage.select_db(self.storage_db)
        self.lib_storage.export_db_to_csv(
            self.storage_structure,
            progress_count_exported_files=self.progress_count_exported_files
        )

    def command_export(self):
        if self.storage_structure:
            self.run_func_in_thread(self.fg_command_export, lambda: self.lib_storage.select_db(self.storage_db))
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

        self.run_func_in_thread(self.fg_command_generate_diff, lambda: self.lib_storage.select_db(self.storage_db))

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


if __name__ == '__main__':
    with LibraryStorage(db_path='') as lib_storage:
        gui = GUI(lib_storage)
        gui.create_window()
        gui.mainloop()
