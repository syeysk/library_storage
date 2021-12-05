from os import curdir, path
from tkinter import Button, filedialog, Label, Tk

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

    def command_scan():
        if storage_directory:
            lib_storage.scan_to_db(
                storage_directory,
                diff_file_path=None,
                delete_dublicate=False,
                progress_count_scanned_files=progress_count_scanned_files
            )
        else:
            print('Пожалуйста, выберите директорию хранилища')

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
        storage_structure = path.dirname(storage_directory)+'/example_csv'#'{}.zip'.format(storage_directory)
        lib_storage = LibraryStorage(db_path=storage_db)
        lib_storage.__enter__()

        val_storage_directory.configure(text=storage_directory)
        val_stat_db_path.configure(text=storage_db)
        val_stat_db_path.configure(text=storage_structure)

    window = Tk()
    window.title("SYeysk LibraryStorage")

    lbl_storage_directory = Label(window, text="Оригинальное хранилище:")
    lbl_storage_directory.grid(column=0, row=0)
    val_storage_directory = Label(window, text="")
    val_storage_directory.grid(column=1, row=0)
    btn_select_storage_directory = Button(window, text="Выбрать", command=select_storage_directory)
    btn_select_storage_directory.grid(column=0, row=1)
    btn_command_scan = Button(window, text="Сканировать", command=command_scan)
    btn_command_scan.grid(column=1, row=1)
    btn_command_export = Button(window, text="Экспорт", command=command_export)
    btn_command_export.grid(column=2, row=1)

    lbl_structure = Label(window, text="Структура хранилища:")
    lbl_structure.grid(column=0, row=2)
    val_structure = Label(window, text="")
    val_structure.grid(column=1, row=2)
    lbl_stat_db_path = Label(window, text="База хранилища:")
    lbl_stat_db_path.grid(column=0, row=3)
    val_stat_db_path = Label(window, text="")
    val_stat_db_path.grid(column=1, row=3)
    lbl_stat_count_files = Label(window, text="Файлов отсканировано:")
    lbl_stat_count_files.grid(column=0, row=4)
    val_stat_count_files = Label(window, text="")
    val_stat_count_files.grid(column=1, row=4)

    window.mainloop()
