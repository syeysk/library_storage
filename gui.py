from os import curdir, path, makedirs
from threading import Thread
from tkinter import Button, filedialog, Frame, Label, LEFT, RIGHT, Tk, TOP

from library_storage import LibraryStorage

storage_directory = None
storage_db = ''
storage_structure = None


with LibraryStorage(db_path=storage_db) as lib_storage:
    def progress_count_exported_files(number_of_current_row, count_rows, csv_current_page):
        text = '{}/{} Страниц: {}'.format(number_of_current_row, count_rows, csv_current_page)
        val_stat_count_files.configure(text=text)

    def progress_count_scanned_files(total_scanned_files):
        val_stat_count_files.configure(text=total_scanned_files)

    def check_command_scan(thread):
        if thread.is_alive():
            window.after(1000, check_command_scan, thread)
            print('поток выполняется')
        else:
            print('поток завершён')

    def fg_command_scan():
        lib_storage.select_db(storage_db)
        lib_storage.scan_to_db(
            storage_directory,
            diff_file_path=None,
            delete_dublicate=False,
            progress_count_scanned_files=progress_count_scanned_files
        )

    def command_scan():
        if not storage_directory:
            print('Пожалуйста, выберите директорию хранилища')
            return

        thread = Thread(None, fg_command_scan)
        thread.start()
        check_command_scan(thread)

    def command_export():
        if storage_structure:
            lib_storage.export_db_to_csv(storage_structure)
            print('Завершено')
        else:
            print('Пожалуйста, выберите директорию структуры')

    def select_storage_directory():
        global storage_db, storage_directory, storage_structure
        storage_directory = filedialog.askdirectory(initialdir=curdir)
        storage_db = '{}.db'.format(storage_directory)
        storage_structure = path.dirname(storage_directory) + '/example_csv'#'{}.zip'.format(storage_directory)
        if not path.exists(storage_structure):
            makedirs(storage_structure, exist_ok=True)

        lib_storage.select_db(storage_db)

        val_storage_directory.configure(text=storage_directory)
        val_stat_db_path.configure(text=storage_db)
        val_structure.configure(text=storage_structure)

    window = Tk()
    window.title("SYeysk LibraryStorage")

    frame_input = Frame(window)
    btn_select_storage_directory = Button(frame_input, text="Выбрать хранилище", command=select_storage_directory)
    btn_select_storage_directory.pack(side=LEFT)
    lbl_storage_directory = Label(frame_input, text="Оригинальное хранилище:")
    lbl_storage_directory.pack(side=LEFT)
    val_storage_directory = Label(frame_input, text="")
    val_storage_directory.pack(side=LEFT)
    frame_input.pack()

    frame_buttons = Frame(window)
    btn_command_export = Button(frame_buttons, text="Экспорт", command=command_export)
    btn_command_export.pack(side=RIGHT)
    btn_command_scan = Button(frame_buttons, text="Сканировать", command=command_scan)
    btn_command_scan.pack(side=RIGHT)
    frame_buttons.pack()

    frame_statistic = Frame(window)
    lbl_structure = Label(frame_statistic, text="Структура хранилища:")
    lbl_structure.pack(side=TOP)
    val_structure = Label(frame_statistic, text="")
    val_structure.pack(side=TOP)
    lbl_stat_db_path = Label(frame_statistic, text="База хранилища:")
    lbl_stat_db_path.pack(side=TOP)
    val_stat_db_path = Label(frame_statistic, text="")
    val_stat_db_path.pack(side=TOP)
    lbl_stat_count_files = Label(frame_statistic, text="Файлов отсканировано:")
    lbl_stat_count_files.pack(side=TOP)
    val_stat_count_files = Label(frame_statistic, text="")
    val_stat_count_files.pack(side=TOP)
    frame_statistic.pack()

    window.mainloop()
