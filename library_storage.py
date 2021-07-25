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
    CSV_COUNT_ROWS_ON_PAGE = 20

    def __init__(self, library_path: str, csv_path: str, db_path: str) -> None:
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
        db_count_pages = total_rows_count // self.DB_COUNT_ROWS_ON_PAGE
        if total_rows_count % self.DB_COUNT_ROWS_ON_PAGE > 0:
            db_count_pages += 1

        sql = 'SELECT hash, id, directory, filename FROM files LIMIT ?,?'
        offset = 0
        total_count_files = 0
        csv_writer = None
        csv_file = None
        csv_current_page = 0
        for _ in range(db_count_pages):
            sql_params = (offset, self.DB_COUNT_ROWS_ON_PAGE)
            rows = self.cu.execute(sql, sql_params).fetchall()
            offset += self.DB_COUNT_ROWS_ON_PAGE
            for row in rows:
                if total_count_files % self.CSV_COUNT_ROWS_ON_PAGE == 0:
                    if csv_file:
                        csv_file.close()

                    csv_current_page += 1
                    csv_full_path = os.path.join(self.csv_path, '{}.csv'.format(str(csv_current_page)))
                    csv_file = open(csv_full_path, 'w', encoding='utf-8', newline='\n')
                    csv_writer = csv.writer(csv_file)

                csv_writer.writerow(row)
                total_count_files += 1
                #print(row)

        if csv_file:
            csv_file.close()

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

    if not os.path.exists(csv_path):
        os.makedirs(csv_path)
    else:
        if not os.path.isdir(csv_path):
            raise Exception('Не я вляется директорией: csv_path =', csv_path)

    lib_storage = LibraryStorage(library_path=library_path, csv_path=csv_path, db_path=db_path)
    lib_storage.scan_to_db()
    lib_storage.export_db_to_csv()
