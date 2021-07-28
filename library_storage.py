import csv
import hashlib
import os
import sqlite3


def get_file_hash(file_path):
    BLOCKSIZE = 65536
    hasher = hashlib.md5()
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
            hash VARCHAR(255) UNIQUE,
            id INTEGER PRIMARY KEY,
            directory VARCHAR(255),
            filename VARCHAR(255),
            is_deleted INT NOT NULL DEFAULT 0
        );'''

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

    def insert_rows(self, with_id: bool = True, do_insert_new: bool = True, func=None) -> None:
        sql = self.SQL_INSERT_ROW_WITH_ID if with_id else self.SQL_INSERT_ROW
        for sql_params in self.seq_sql_params:
            file_hash = sql_params[0]
            sql_select = 'SELECT id, directory, filename FROM files WHERE hash=?'
            is_exists = self.cu.execute(sql_select, (file_hash,)).fetchone()
            inserted_directory, inserted_filename = sql_params[2 if with_id else 1:]
            inserted_path = '{}/{}'.format(inserted_directory, inserted_filename)  # .removeprefix('/')
            inserted_path = inserted_path[1:] if inserted_path.startswith('/') else inserted_path
            if not is_exists:
                if do_insert_new:
                    self.cu.execute(sql, sql_params)

                func_row = ('Новый', inserted_path)
            else:
                existed_directory, existed_filename = is_exists[1:]
                existed_path = '{}/{}'.format(existed_directory, existed_filename)  # .removeprefix('/')
                existed_path = existed_path[1:] if existed_path.startswith('/') else existed_path
                is_replaced = inserted_directory != existed_directory
                is_renamed = inserted_filename != existed_filename
                if is_replaced and not is_renamed:
                    func_row = ('Переместили', existed_path, '->', inserted_path)
                elif not is_replaced and is_renamed:
                    func_row = ('Переименовали', existed_path, '->', inserted_path)
                elif is_replaced and is_renamed:
                    func_row = ('Переместили и переименовали', existed_path, '->', inserted_path)
                else:
                    func_row = ('Не тронут', existed_path)

                self.cu.execute('UPDATE files SET is_deleted=0 WHERE hash=?', (file_hash,))

            if func:
                func(func_row)

        # try:
        #     self.cu.executemany(sql, self.seq_sql_params)
        # except sqlite3.IntegrityError as error:
        #     print(error)
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
        for row in self.select_rows(only_deleted=True):
            existed_directory, existed_filename = row[2:]
            existed_path = '{}/{}'.format(existed_directory, existed_filename)  # .removeprefix('/')
            existed_path = existed_path[1:] if existed_path.startswith('/') else existed_path
            func(('Удалён', existed_path))


# sqlite3.IntegrityError: UNIQUE constraint failed: files.hash
class LibraryStorage:
    CSV_COUNT_ROWS_ON_PAGE = 20
    DIFF_FILE_NAME = 'diff.csv'

    def __init__(self, library_path: str, csv_path: str, db_path: str, diff_path: str) -> None:
        """
        Инициализирует класс хранилища
        :param library_path:
        :param db_path:
        :param name:
        """
        self.csv_path = csv_path
        self.library_path = library_path
        self.diff_path = diff_path
        os.chdir(library_path)
        self.db = DBStorage(db_path=db_path)

    def __enter__(self):
        return self

    def __exit__(self, _1, _2, _3):
        self.db.c.close()

    def scan_to_db(self, library_path=None) -> None:
        """Сканирует информацию о файлах в директории и заносит её в базу"""
        self.db.set_is_deleted()
        if library_path is None:
            library_path = self.library_path

        with open(os.path.join(self.diff_path, self.DIFF_FILE_NAME), 'w', encoding='utf-8', newline='\n') as diff_file:
            diff_csv = csv.writer(diff_file)
            os.chdir(library_path)
            total_count_files = 0
            for directory, _, filenames in os.walk('./'):
                directory = directory[2:]
                if os.path.sep == '\\':
                    directory = directory.replace('\\', '/')

                for filename in filenames:
                    file_hash = get_file_hash(os.path.join(directory, filename))
                    self.db.append_row((file_hash, directory, filename))
                    total_count_files += 1
                    if self.db.is_ready_for_insert():
                        self.db.insert_rows(with_id=False, func=diff_csv.writerow)

                    #print((file_hash, directory, filename))

            self.db.insert_rows(with_id=False, func=diff_csv.writerow)
            self.db.print_deleted_files(func=diff_csv.writerow)
            print('Обнаружено файлов:', total_count_files, 'шт')

    def export_db_to_csv(self) -> None:
        """
        Экспортирует из базы метаинформацию в CSV без заголовков. Формат строки следующий:
        хэш,идентификатор,директория,имя файла
        """
        csv_writer = None
        csv_file = None
        csv_current_page = 0
        total_count_files = None
        for total_count_files, row in enumerate(self.db.select_rows()):
            if total_count_files % self.CSV_COUNT_ROWS_ON_PAGE == 0:
                if csv_file:
                    csv_file.close()

                csv_current_page += 1
                csv_full_path = os.path.join(self.csv_path, '{}.csv'.format(str(csv_current_page)))
                csv_file = open(csv_full_path, 'w', encoding='utf-8', newline='\n')
                csv_writer = csv.writer(csv_file)

            csv_writer.writerow(row)
            #print(row)

        if csv_file:
            csv_file.close()

        print('Экспортировано файлов:', total_count_files, 'шт')

    def import_csv_to_db(self) -> None:
        for csv_filename in os.scandir(self.csv_path):
            with open(csv_filename.path, 'r', encoding='utf-8', newline='\n') as csv_file:
                for csv_row in csv.reader(csv_file):
                    self.db.append_row(tuple(csv_row))
                    if self.db.is_ready_for_insert():
                        self.db.insert_rows()

        self.db.insert_rows()


if __name__ == '__main__':
    repository_path = os.path.dirname(__file__)
    #library_path = 'C:\\test\\Статьи'
    library_path = os.path.join(repository_path, 'example_library_origin')
    library_path_changed = os.path.join(repository_path, 'example_library_changed')
    csv_path = os.path.join(repository_path, 'example_csv')
    diff_path = os.path.join(repository_path, 'example_diff')
    db_path = ':memory:'

    if not os.path.exists(csv_path):
        os.makedirs(csv_path)
    else:
        if not os.path.isdir(csv_path):
            raise Exception('Не является директорией: csv_path =', csv_path)

    if not os.path.exists(diff_path):
        os.makedirs(diff_path)
    else:
        if not os.path.isdir(diff_path):
            raise Exception('Не является директорией: diff_path =', diff_path)

    with LibraryStorage(library_path=library_path, csv_path=csv_path, db_path=db_path, diff_path=diff_path) as lib_storage:
        lib_storage.scan_to_db()
        lib_storage.export_db_to_csv()
        print('Кол-во строк до очистки:', lib_storage.db.get_count_rows())
        lib_storage.db.clear()
        print('Кол-во строк после очистки:', lib_storage.db.get_count_rows())
        lib_storage.import_csv_to_db()
        print('Кол-во строк после импорта:', lib_storage.db.get_count_rows())
        print('\nСканируем изменённую базу...')
        lib_storage.scan_to_db(library_path=library_path_changed)
