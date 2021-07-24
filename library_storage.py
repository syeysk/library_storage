import os
import sqlite3
import hashlib


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

    def __init__(self, db_path=':memory:'):
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

    def scan_to_db(self, library_path):
        sql = 'INSERT INTO files (hash, directory, filename) VALUES (?, ?, ?)'
        seq_sql_params = []
        for directory, _, filenames in os.walk(library_path):
            for filename in filenames:
                file_hash = get_file_hash(os.path.join(directory, filename))
                seq_sql_params.append((file_hash, directory, filename))
                if len(seq_sql_params) == self.DB_COUNT_ROWS_FOR_INSERT:
                    self.cu.executemany(sql, seq_sql_params)
                    seq_sql_params.clear()

                print((file_hash, directory, filename))

        if seq_sql_params:
            self.cu.executemany(sql, seq_sql_params)
            seq_sql_params.clear()

    def export_db_to_csv(self):
        total_rows_count = self.cu.execute('SELECT COUNT(id) AS total_rows_count FROM files').fetchone()
        total_rows_count = total_rows_count[0]
        count_pages = total_rows_count // self.DB_COUNT_ROWS_ON_PAGE
        if total_rows_count % self.DB_COUNT_ROWS_ON_PAGE > 0:
            count_pages += 1

        sql = 'SELECT hash, id, directory, filename FROM files LIMIT ?,?'
        offset = 0
        for current_page in range(count_pages):
            sql_params = (offset, self.DB_COUNT_ROWS_ON_PAGE)
            rows = self.cu.execute(sql, sql_params).fetchall()
            offset += self.DB_COUNT_ROWS_ON_PAGE
            for row in rows:
                print(row)

    def import_csv_to_db(self):
        ...


if __name__ == '__main__':
    library_path = 'C:\\test\\Статьи'

    lib_storage = LibraryStorage()
    lib_storage.scan_to_db(library_path)
    lib_storage.export_db_to_csv()
