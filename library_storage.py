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

# sqlite3.IntegrityError: UNIQUE constraint failed: files.hash
class LibraryStorage:
    DB_COUNT_ROWS_FOR_INSERT = 100
    DB_COUNT_ROWS_ON_PAGE = 10

    def __init__(self, library_path, csv_path, db_path):
        """
        Инициализирует класс хранилища
        :param library_path:
        :param db_path:
        :param name:
        """
        self.c = sqlite3.connect(db_path)
        self.cu = self.c.cursor()
        self.cu.executescript('''
CREATE TABLE IF NOT EXISTS files (
    hash VARCHAR(255) UNIQUE,
    id INTEGER PRIMARY KEY,
    directory VARCHAR(255),
    filename VARCHAR(255)
);
        ''')
        self.csv_path = csv_path
        self.library_path = library_path
        os.chdir(library_path)

    def scan_to_db(self) -> None:
        """Сканирует информацию о файлах в директории и заносит её в базу"""
        sql = 'INSERT INTO files (hash, directory, filename) VALUES (?, ?, ?)'
        seq_sql_params = []
        total_count_files = 0
        for directory, _, filenames in os.walk('./'):
            directory = directory[2:]
            if os.path.sep == '\\':
                directory = directory.replace('\\', '/')

            for filename in filenames:
                file_hash = get_file_hash(os.path.join(directory, filename))
                seq_sql_params.append((file_hash, directory, filename))
                total_count_files += 1
                if len(seq_sql_params) == self.DB_COUNT_ROWS_FOR_INSERT:
                    self.cu.executemany(sql, seq_sql_params)
                    seq_sql_params.clear()

                #print((file_hash, directory, filename))

        if seq_sql_params:
            self.cu.executemany(sql, seq_sql_params)
            seq_sql_params.clear()

        print('Обнаружено файлов:', total_count_files, 'шт')

    def export_db_to_csv(self) -> None:
        """
        Экспортирует из базы метаинформацию в CSV без заголовков. Формат строки следующий:
        хэш,идентификатор,директория,имя файла
        """
        total_rows_count = self.cu.execute('SELECT COUNT(id) AS total_rows_count FROM files').fetchone()
        total_rows_count = total_rows_count[0]
        count_pages = total_rows_count // self.DB_COUNT_ROWS_ON_PAGE
        if total_rows_count % self.DB_COUNT_ROWS_ON_PAGE > 0:
            count_pages += 1

        sql = 'SELECT hash, id, directory, filename FROM files LIMIT ?,?'
        offset = 0
        total_count_files = 0
        for current_page in range(count_pages):
            sql_params = (offset, self.DB_COUNT_ROWS_ON_PAGE)
            rows = self.cu.execute(sql, sql_params).fetchall()
            offset += self.DB_COUNT_ROWS_ON_PAGE
            for row in rows:
                total_count_files += 1
                #print(row)

        print('Экспортировано файлов:', total_count_files, 'шт')

    def import_csv_to_db(self) -> None:
        ...

    def check_diff(self, library_path) -> None:
        """
        Проверяет различия в двух базах. Выявляет следующие различия файлов:
        - переименован/перемещён
        - удалён
        - добавлен
        :param source_library_db:
        :param library_path:
        :return:
        """


if __name__ == '__main__':
    library_path = 'C:\\test\\Статьи'
    csv_path = os.path.join(os.path.dirname(__file__), 'csv_articles')
    db_path = ':memory:'

    lib_storage = LibraryStorage(library_path=library_path, csv_path=csv_path, db_path=db_path)
    lib_storage.scan_to_db()
    lib_storage.export_db_to_csv()
