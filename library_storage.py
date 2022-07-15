import csv
import hashlib
import os
import sqlite3
import zipfile
from io import TextIOWrapper, StringIO


STATUS_NEW = 'Новый'
STATUS_MOVED = 'Переместили'
STATUS_RENAMED = 'Переименовали'
STATUS_MOVED_AND_RENAMED = 'Переместили и переименовали'
STATUS_UNTOUCHED = 'Не тронут'
STATUS_DELETED = 'Удалён'


def get_file_hash(file_path):
    BLOCKSIZE = 65536
    hasher = hashlib.blake2s()
    with open(file_path, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)

    return hasher.hexdigest()


class DBStorage:
    COUNT_ROWS_FOR_INSERT = 30
    COUNT_ROWS_ON_PAGE = 10
    SQL_INSERT_ROW = 'INSERT INTO files (hash, directory, filename) VALUES (?, ?, ?)'
    SQL_INSERT_ROW_WITH_ID = 'INSERT INTO files (hash, id, directory, filename) VALUES (?, ?, ?, ?)'
    SQL_SELECT_COUNT_ROWS = 'SELECT COUNT(id) FROM files'
    SQL_SELECT_ROWS = 'SELECT hash, id, directory, filename FROM files LIMIT ?,?'
    SQL_SELECT_ROWS_ONLY_DELETED = 'SELECT hash, id, directory, filename FROM files WHERE is_deleted=1 LIMIT ?,?'
    SQL_UPDATE_SET_IS_DELETED = 'UPDATE files SET is_deleted=1'
    SQL_CREATE_TABLE = '''
        CREATE TABLE IF NOT EXISTS files (
            hash VARCHAR(64) UNIQUE,
            id INTEGER PRIMARY KEY,
            directory VARCHAR(255),
            filename VARCHAR(255),
            is_deleted INT NOT NULL DEFAULT 0
        );'''
    SQL_DELETE_FILE = 'DELETE FROM files WHERE hash=?'

    def __init__(self, db_path: str) -> None:
        self.c = sqlite3.connect(db_path)
        self.cu = self.c.cursor()
        self.cu.executescript(self.SQL_CREATE_TABLE)
        self.seq_sql_params = []

    def clear(self) -> None:
        self.cu.execute('DELETE FROM files WHERE 1=1')
        self.c.commit()

    def get_count_rows(self) -> int:
        total_rows_count = self.cu.execute(self.SQL_SELECT_COUNT_ROWS).fetchone()
        return total_rows_count[0]

    def get_count_pages(self) -> int:
        total_rows_count = self.get_count_rows()
        count_pages = total_rows_count // self.COUNT_ROWS_ON_PAGE
        return count_pages + 1 if total_rows_count % self.COUNT_ROWS_ON_PAGE > 0 else count_pages

    def append_row(self, row: tuple) -> None:
        self.seq_sql_params.append(row)

    def is_ready_for_insert(self) -> bool:
        return len(self.seq_sql_params) == self.COUNT_ROWS_FOR_INSERT

    def insert_rows(
            self,
            with_id: bool = True,
            do_insert_new: bool = True,
            func=None,
            delete_dublicate: bool = False
    ) -> tuple:
        """
        Добавляет список файлов в базу
        :param with_id:
        :param do_insert_new:
        :param func:
        :param delete_dublicate: если Истина, то будет удалять с диска файлы с одинаковым хешем,
        иначе - возбуждать исключение
        :return:
        """
        sql = self.SQL_INSERT_ROW_WITH_ID if with_id else self.SQL_INSERT_ROW
        for sql_params in self.seq_sql_params:
            file_hash = sql_params[0]
            sql_select = 'SELECT id, directory, filename FROM files WHERE hash=?'
            is_exists = self.cu.execute(sql_select, (file_hash,)).fetchone()
            inserted_directory, inserted_filename = sql_params[2 if with_id else 1:]
            existed_directory, existed_filename = None, None
            if is_exists:
                existed_directory, existed_filename = is_exists[1:]
                self.cu.execute('UPDATE files SET is_deleted=0 WHERE hash=?', (file_hash,))

                print('Обнаружен дубликат по хешу: {}\n    В базе:{}'.format(
                    os.path.join(inserted_directory, inserted_filename),
                    os.path.join(existed_directory, existed_filename),
                ))
            else:
                if do_insert_new:
                    try:
                        self.cu.execute(sql, sql_params)
                    except sqlite3.IntegrityError as error:
                        if not delete_dublicate:
                            raise Exception('Обнаружен дубликат файла с отличающимся именем среди порции вставляемых файлов: {}'.format(error))

                        print(error)  # TODO удалять файлы с разным именем, но с одинаковым хешем.

            if func:
                func(inserted_directory, inserted_filename, is_exists, existed_directory, existed_filename)

        self.c.commit()
        self.seq_sql_params.clear()

    def select_rows(self, only_deleted=False):
        sql = self.SQL_SELECT_ROWS_ONLY_DELETED if only_deleted else self.SQL_SELECT_ROWS
        count_pages = self.get_count_pages()
        for page_num in range(count_pages):
            sql_params = (page_num * self.COUNT_ROWS_ON_PAGE, self.COUNT_ROWS_ON_PAGE)
            for row in self.cu.execute(sql, sql_params).fetchall():
                yield row

    def set_is_deleted(self):
        self.cu.execute(self.SQL_UPDATE_SET_IS_DELETED)
        self.c.commit()

    def print_deleted_files(self, func):
        for file_hash, file_id, existed_directory, existed_filename in self.select_rows(only_deleted=True):
            existed_path = '{}/{}'.format(existed_directory, existed_filename)  # .removeprefix('/')
            existed_path = existed_path[1:] if existed_path.startswith('/') else existed_path
            func((STATUS_DELETED, existed_path, None, file_hash, file_id))

    def delete_file(self, file_hash):
        self.cu.execute(self.SQL_DELETE_FILE, (file_hash, ))
        self.c.commit()


class LibraryStorage:
    CSV_COUNT_ROWS_ON_PAGE = 100
    ARCHIVE_DIFF_FILE_NAME = 'diff.csv'

    def __init__(self, db_path: str) -> None:
        """
        Инициализирует класс хранилища
        :param db_path:
        :param name:
        """
        self.db = DBStorage(db_path=db_path)

    def __enter__(self):
        return self

    def __exit__(self, _1, _2, _3):
        self.db.c.close()

    def select_db(self, db_path: str):
        self.db = DBStorage(db_path=db_path)

    def scan_to_db(
            self,
            library_path,
            delete_dublicate=False,
            progress_count_scanned_files=None
    ) -> None:
        """Сканирует информацию о файлах в директории и заносит её в базу"""
        def print_file_status(inserted_directory, inserted_filename, is_exists, existed_directory, existed_filename):
            status, existed_path, inserted_path = self.print_file_status(
                inserted_directory,
                inserted_filename,
                is_exists,
                existed_directory,
                existed_filename
            )
            if status != STATUS_UNTOUCHED:
                self.diffs.append((status, existed_path, inserted_path))

        self.db.set_is_deleted()
        os.chdir(library_path)
        total_count_files = 0
        self.diffs = []
        for directory, _, filenames in os.walk('./'):
            directory = directory[2:]
            if os.path.sep == '\\':
                directory = directory.replace('\\', '/')

            for filename in filenames:
                file_hash = get_file_hash(os.path.join(directory, filename))
                self.db.append_row((file_hash, directory, filename))
                total_count_files += 1
                if progress_count_scanned_files:
                    progress_count_scanned_files(total_count_files)

                if self.db.is_ready_for_insert():
                    self.db.insert_rows(with_id=False, func=print_file_status, delete_dublicate=delete_dublicate)

        self.db.insert_rows(with_id=False, func=print_file_status, delete_dublicate=delete_dublicate)
        print('Обнаружено файлов:', total_count_files, 'шт')

    def export_db_to_csv(self, csv_path, progress_count_exported_files=None) -> None:
        """
        Экспортирует из базы метаинформацию в CSV без заголовков. Формат строки следующий:
        хэш,идентификатор,директория,имя файла
        """
        csv_writer = None
        csv_file = None
        csv_current_page = 0
        number_of_last_row_on_current_page = self.CSV_COUNT_ROWS_ON_PAGE
        count_rows = self.db.get_count_rows() if progress_count_exported_files else None
        number_of_current_row = None
        for number_of_current_row, row in enumerate(self.db.select_rows()):
            number_of_last_row_on_current_page = number_of_last_row_on_current_page - row[1] + 1
            if csv_writer is None or number_of_current_row == number_of_last_row_on_current_page:
                if csv_file:
                    csv_file.close()

                number_of_last_row_on_current_page += self.CSV_COUNT_ROWS_ON_PAGE
                csv_current_page += 1
                csv_full_path = os.path.join(csv_path, '{}.csv'.format(str(csv_current_page)))
                csv_file = open(csv_full_path, 'w', encoding='utf-8', newline='\n')
                csv_writer = csv.writer(csv_file)
                if progress_count_exported_files:
                    progress_count_exported_files(number_of_current_row + 1, count_rows, csv_current_page)

            csv_writer.writerow(row)
            number_of_last_row_on_current_page += row[1]

        if progress_count_exported_files:
            progress_count_exported_files(number_of_current_row + 1, count_rows, csv_current_page)

        if csv_file:
            csv_file.close()

    def import_csv_to_db(self, csv_path):
        for csv_filename in os.scandir(csv_path):
            with open(csv_filename.path, 'r', encoding='utf-8', newline='\n') as csv_file:
                for csv_row in csv.reader(csv_file):
                    self.db.append_row(tuple(csv_row))
                    if self.db.is_ready_for_insert():
                        self.db.insert_rows()

        self.db.insert_rows()

    def save_diff(self, library_path, diff_file_path):
        diff_zip = zipfile.ZipFile(diff_file_path, 'w')
        diff_file = StringIO()
        diff_csv = csv.writer(diff_file)
        for status, existed_path, inserted_path in self.diffs:
            diff_csv.writerow((status, existed_path, inserted_path))
            if status == STATUS_NEW:
                diff_zip.write(os.path.join(library_path, inserted_path), os.path.join('storage', inserted_path))

        self.db.print_deleted_files(func=diff_csv.writerow)
        diff_zip.writestr(self.ARCHIVE_DIFF_FILE_NAME, diff_file.getvalue())
        diff_zip.close()

    def apply_diff(self, library_path, diff_file_zip_path):
        with zipfile.ZipFile(diff_file_zip_path, 'r') as diff_zip:
            diff_zip.testzip()
            with diff_zip.open(self.ARCHIVE_DIFF_FILE_NAME, 'r') as diff_file:
                diff_file_io = TextIOWrapper(diff_file, encoding='utf-8')
                diff_csv = csv.reader(diff_file_io)
                for status, existed_file, inserted_file, file_hash, file_id in diff_csv:
                    if existed_file:
                        full_existed_path = os.path.join(library_path, existed_file)
                        full_existed_path = os.path.normpath(full_existed_path)

                    if inserted_file:
                        full_inserted_path = os.path.join(library_path, inserted_file)
                        full_inserted_path = os.path.normpath(full_inserted_path)

                    if status == STATUS_NEW:
                        if os.path.exists(full_inserted_path):
                            print(status, 'Файл существует:', full_inserted_path)

                        diff_zip.extract(os.path.join('storage', inserted_file), library_path)
                    elif status == STATUS_DELETED:
                        os.unlink(full_existed_path)
                        self.db.delete_file(file_hash)
                    elif status in (STATUS_MOVED, STATUS_RENAMED, STATUS_MOVED_AND_RENAMED):
                        if os.path.exists(full_inserted_path):
                            print(status, 'Файл существует:', full_inserted_path)

                        os.rename(full_existed_path, full_inserted_path)

                diff_file.close()

    def print_file_status(self, inserted_directory, inserted_filename, is_exists, existed_directory, existed_filename):
        inserted_path = '{}/{}'.format(inserted_directory, inserted_filename)  # .removeprefix('/')
        inserted_path = inserted_path[1:] if inserted_path.startswith('/') else inserted_path
        if is_exists:
            existed_path = '{}/{}'.format(existed_directory, existed_filename)  # .removeprefix('/')
            existed_path = existed_path[1:] if existed_path.startswith('/') else existed_path
            is_replaced = inserted_directory != existed_directory
            is_renamed = inserted_filename != existed_filename
            if is_replaced and not is_renamed:
                return STATUS_MOVED, existed_path, inserted_path
            elif not is_replaced and is_renamed:
                return STATUS_RENAMED, existed_path, inserted_path
            elif is_replaced and is_renamed:
                return STATUS_MOVED_AND_RENAMED, existed_path, inserted_path

            return STATUS_UNTOUCHED, existed_path, inserted_path

        return STATUS_NEW, None, inserted_path


def scan_storage_and_save_structure(path_to_library, path_for_save_struct):
    with LibraryStorage(':memory:') as lib_storage:
        lib_storage.scan_to_db(library_path=path_to_library)
        lib_storage.export_db_to_csv(csv_path=path_for_save_struct)


def scan_storage_and_save_diff(path_to_library, path_to_struct, path_to_save_diff):
    with LibraryStorage(':memory:') as lib_storage:
        lib_storage.import_csv_to_db(path_to_struct)
        lib_storage.scan_to_db(library_path=path_to_library)
        lib_storage.save_diff(library_path=path_to_library, diff_file_path=path_to_save_diff)


def apply_diff(path_to_library, path_to_diff):
    with LibraryStorage(':memory:') as lib_storage:
        lib_storage.scan_to_db(library_path=path_to_library)
        lib_storage.apply_diff(library_path=path_to_library, diff_file_zip_path=path_to_diff)


if __name__ == '__main__':
    repository_path = os.path.dirname(__file__)
    #library_path = 'C:\\test\\Статьи'
    library_path = os.path.join(repository_path, 'example_library_origin')
    library_path_changed = os.path.join(repository_path, 'example_library_changed')
    csv_path = os.path.join(repository_path, 'example_csv')
    diff_file_path = os.path.join(repository_path, 'example_diff.zip')
    db_path = ':memory:'
    os.chdir(library_path)

    if not os.path.exists(csv_path):
        os.makedirs(csv_path)
    else:
        if not os.path.isdir(csv_path):
            raise Exception('Не является директорией: csv_path =', csv_path)

    with LibraryStorage(db_path=db_path) as lib_storage:
        lib_storage.scan_to_db(library_path=library_path)
        lib_storage.export_db_to_csv(csv_path)
        print('Кол-во строк до очистки:', lib_storage.db.get_count_rows())
        lib_storage.db.clear()
        print('Кол-во строк после очистки:', lib_storage.db.get_count_rows())
        lib_storage.import_csv_to_db(csv_path)
        print('Кол-во строк после импорта:', lib_storage.db.get_count_rows())
        print('\nСканируем изменённую базу...')
        lib_storage.scan_to_db(library_path=library_path_changed)
        lib_storage.save_diff(library_path=library_path_changed, diff_file_path=diff_file_path)
        library_path_copy = '{}_copy'.format(library_path)
        for directory_path, directories, filenames in os.walk(library_path):
            directory_copy = directory_path[len(library_path)+1:]
            directory_copy = os.path.join(library_path_copy, directory_copy)
            for filename in filenames:
                file_path = os.path.normpath(os.path.join(directory_path, filename))
                file_path_copy = os.path.normpath(os.path.join(directory_copy, filename))
                dirname_copy = os.path.dirname(file_path_copy)
                if not os.path.exists(dirname_copy):
                    os.makedirs(dirname_copy)

                with open(file_path, 'rb') as file_orig, open(file_path_copy, 'wb') as file_copy:
                    file_copy.write(file_orig.read())

            for directory in directories:
                file_path = os.path.normpath(os.path.join(directory_path, directory))
                file_path_copy = os.path.normpath(os.path.join(directory_copy, directory))
                if not os.path.exists(file_path_copy):
                    os.makedirs(file_path_copy)

        lib_storage.apply_diff(library_path=library_path_copy, diff_file_zip_path=diff_file_path)