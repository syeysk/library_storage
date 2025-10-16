import csv
import hashlib
import os
import sqlite3
import zipfile
from io import TextIOWrapper, StringIO
from pathlib import Path

STATUS_NEW = 'Новый'
STATUS_MOVED = 'Переместили'
STATUS_RENAMED = 'Переименовали'
STATUS_MOVED_AND_RENAMED = 'Переместили и переименовали'
STATUS_UNTOUCHED = 'Не тронут'
STATUS_DELETED = 'Удалён'
STATUS_DUPLICATE = 'Дубликат'
LIBRARY_IGNORE_EXTENSIONS = ['mp3', 'db', 'db-journal']


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
    SQL_SELECT_FILE = 'SELECT directory, filename FROM files WHERE hash=?'
    SQL_SELECT_COUNT_ROWS = 'SELECT COUNT(id) FROM files WHERE is_deleted = 0'
    SQL_CREATE_TABLE = '''
        CREATE TABLE IF NOT EXISTS files (
            hash VARCHAR(64) UNIQUE,
            id INTEGER PRIMARY KEY,
            directory VARCHAR(255),
            filename VARCHAR(255),
            is_deleted INT NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255),
            parent INTEGER DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS file_tag (
            file_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL
        );'''
    SQL_DELETE_FILE = 'DELETE FROM files WHERE hash=?'
    SQL_UPDATE_SET_IS_DELETED_FOR_ALL = 'UPDATE files SET is_deleted=1'
    SQL_UPDATE_SET_IS_DELETED = 'UPDATE files SET is_deleted=0 WHERE hash=?'
    SQL_UPDATE_FILE = 'UPDATE files SET directory=?, filename=? WHERE hash=?'

    SQL_INSERT_TAG = 'INSERT INTO tags (name, parent) VALUES (?, ?)'
    SQL_SELECT_TAGS = 'SELECT id, name FROM tags WHERE parent=?'
    SQL_SELECT_TAGS_NULL = 'SELECT id, name FROM tags WHERE parent IS NULL'
    SQL_SELECT_ALL_TAGS = 'SELECT id, name, parent FROM tags'
    SQL_SELECT_TAG = 'SELECT name, parent FROM tags WHERE id=?'
    
    SQL_SELECT_TAGS_BY_FILE = 'SELECT tags.name, tags.id FROM file_tag INNER JOIN tags ON file_tag.tag_id = tags.id WHERE file_tag.file_id=? ORDER BY tags.name'
    SQL_INSERT_TAG_TO_FILE = 'INSERT INTO file_tag (file_id, tag_id) VALUES (?, ?)'
    SQL_CHECK_TAG_FILE = 'SELECT 1 FROM file_tag WHERE file_id=? AND tag_id=? LIMIT 1'
    SQL_DELETE_TAG_FROM_FILE = 'DELETE FROM file_tag WHERE file_id=? AND tag_id=?'

    def insert_tag(self, name, parent=None):
        self.cu.execute(self.SQL_INSERT_TAG, (name, parent))
        tag_id = self.cu.lastrowid
        self.c.commit()
        return tag_id

    def select_tags(self, parent=None):
        sql = self.SQL_SELECT_TAGS if parent else self.SQL_SELECT_TAGS_NULL
        params = (parent,) if parent else ()
        for row in self.cu.execute(sql, params).fetchall():
            yield row

    def select_all_tags(self):
        for row in self.cu.execute(self.SQL_SELECT_ALL_TAGS).fetchall():
            yield row

    def select_tag(self, tag_id):
        return self.cu.execute(self.SQL_SELECT_TAG, (tag_id,)).fetchone()

    def select_tags_by_file(self, file_id):
        for row in self.cu.execute(self.SQL_SELECT_TAGS_BY_FILE, (file_id,)).fetchall():
            yield row

    def assign_tag(self, tag_id, file_id):
        sql_params = (file_id, tag_id)
        if self.cu.execute(self.SQL_CHECK_TAG_FILE, sql_params).fetchone():
            return False

        self.cu.execute(self.SQL_INSERT_TAG_TO_FILE, sql_params)
        self.c.commit()
        return True

    def unassign_tag(self, tag_id, file_id):
        sql_params = (file_id, tag_id)
        self.cu.execute(self.SQL_DELETE_TAG_FROM_FILE, sql_params)
        self.c.commit()

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.c = sqlite3.connect(db_path)
        self.cu = self.c.cursor()
        self.cu.executescript(self.SQL_CREATE_TABLE)
        self.seq_sql_params = []
        self.duplicates_by_hash = {}

    def reopen(self):
        """
        Переоткрывает существующую базу.
        Вызываем метод внутри дочернего потока и после выхода из дочернего потока - в родительском """
        self.c = sqlite3.connect(self.db_path)
        self.cu = self.c.cursor()

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

    def insert_rows(self, with_id: bool = True, func=None):
        """
        Добавляет список файлов в базу
        :param with_id:
        :param func:
        иначе - возбуждать исключение
        :return:
        """
        sql_insert = self.SQL_INSERT_ROW_WITH_ID if with_id else self.SQL_INSERT_ROW
        for sql_params in self.seq_sql_params:
            file_hash = sql_params[0]
            row = self.cu.execute(self.SQL_SELECT_FILE, (file_hash,)).fetchone()
            inserted_directory, inserted_filename = sql_params[2 if with_id else 1:]
            if row:
                existed_directory, existed_filename = row
                self.set_is_not_deleted(file_hash)
            else:
                self.cu.execute(sql_insert, sql_params)
                existed_directory, existed_filename = None, None

            if func:
                func(
                    inserted_directory,
                    inserted_filename,
                    existed_directory,
                    existed_filename,
                    file_hash,
                )

        self.c.commit()
        self.seq_sql_params.clear()

    def select_rows(self, tags=None, only_deleted=False):
        sql_params = []
        sql = ['SELECT files.hash, files.id, files.directory, files.filename FROM files']
        sql_where = []
        
        if tags:
            sql.append('JOIN file_tag ON files.id = file_tag.file_id')
        
        if tags:
            sql_where.append('file_tag.tag_id IN (%s)' % ', '.join('?'*len(tags)))
            sql_params.extend(tags)

        if only_deleted:
            sql_where.append('files.is_deleted = 1')

        if sql_where:
            sql.append('WHERE')
            sql.append(' AND '.join(sql_where))

        sql.append('GROUP BY files.id ORDER BY files.filename LIMIT ?,?')
        sql = ' '.join(sql)

        count_pages = self.get_count_pages()
        for page_num in range(count_pages):
            all_sql_params = [*sql_params, page_num * self.COUNT_ROWS_ON_PAGE, self.COUNT_ROWS_ON_PAGE]
            for row in self.cu.execute(sql, all_sql_params).fetchall():
                yield row

    def set_is_deleted_for_all(self):
        self.cu.execute(self.SQL_UPDATE_SET_IS_DELETED_FOR_ALL)
        self.c.commit()

    def set_is_not_deleted(self, file_hash):
        self.cu.execute(self.SQL_UPDATE_SET_IS_DELETED, (file_hash,))

    def print_deleted_files(self, func):
        for file_hash, file_id, existed_directory, existed_filename in self.select_rows(only_deleted=True):
            existed_path = '{}/{}'.format(existed_directory, existed_filename)  # .removeprefix('/')
            existed_path = existed_path[1:] if existed_path.startswith('/') else existed_path
            func(STATUS_DELETED, existed_path, None, file_hash, file_id)

    def delete_file(self, file_hash):
        self.cu.execute(self.SQL_DELETE_FILE, (file_hash, ))
        self.c.commit()

    def insert_file(self, file_hash, file_id, inserted_file):
        self.cu.execute(
            self.SQL_INSERT_ROW_WITH_ID,
            (file_hash, file_id, os.path.dirname(inserted_file), os.path.basename(inserted_file))
        )
        self.c.commit()

    def update(self, file_hash, inserted_directory, inserted_filename):
        self.cu.execute(self.SQL_UPDATE_FILE, (inserted_directory, inserted_filename, file_hash))


class LibraryStorage:
    CSV_COUNT_ROWS_ON_PAGE = 100
    ARCHIVE_DIFF_FILE_NAME = 'diff.csv'
    MESSAGE_DOUBLE = 'Обнаружен дубликат по хешу:\n   В базе: {}\n    Дубль: {}'
    MESSAGE_DOUBLE_IMPORT = (
        'Обнаружен дубликат файла с отличающимся именем среди порции вставляемых файлов: '
        '{}\n    В базе:{}'
    )

    def __init__(self) -> None:
        """Инициализирует класс сканера хранилища"""
        self.db = None

    def __enter__(self):
        return self

    def __exit__(self, _1, _2, _3):
        if self.db:
            self.db.c.close()

    def set_db(self, db):
        self.db = db

    def scan_to_db(
            self,
            library_path: Path,
            process_dublicate,
            progress_count_scanned_files=None,
            func=None,
    ):
        """Сканирует информацию о файлах в директории и заносит её в базу"""
        def process_file_status(inserted_directory,
                    inserted_filename,
                    existed_directory,
                    existed_filename,
                    file_hash,):
            status, existed_path, inserted_path = self.get_file_status(inserted_directory, inserted_filename, existed_directory, existed_filename)
            if status != STATUS_NEW:
                if process_dublicate == 'original':
                    if status in {STATUS_MOVED, STATUS_RENAMED, STATUS_MOVED_AND_RENAMED}:
                        self.db.update(file_hash, inserted_directory, inserted_filename)

            if func:
                func(status, existed_path, inserted_path, file_hash)

        self.db.set_is_deleted_for_all()
        os.chdir(library_path)
        total_count_files = 0
        for directory, _, filenames in os.walk('./'):
            directory = directory[2:]
            if os.path.sep == '\\':
                directory = directory.replace('\\', '/')

            for filename in filenames:
                if filename.split('.')[-1] in LIBRARY_IGNORE_EXTENSIONS:
                    continue  # останется отмеченным как удалённый, а потому в структуру (экспорт) не попадёт

                file_hash = get_file_hash(os.path.join(directory, filename))
                self.db.append_row((file_hash, directory, filename))
                total_count_files += 1
                if progress_count_scanned_files:
                    progress_count_scanned_files(total_count_files)

                if self.db.is_ready_for_insert():
                    self.db.insert_rows(with_id=False, func=process_file_status)

        self.db.insert_rows(with_id=False, func=process_file_status)
        # print('Обнаружено файлов:', total_count_files, 'шт')
        #self.db.print_deleted_files(process_file_status)

    def export_db(self, exporter, progress_count_exported_files=None) -> None:
        """
        Экспортирует из базы следующую информацию о файле:
        хэш,идентификатор,директория,имя файла
        """
        csv_current_page = 1
        exporter.open_new_page(csv_current_page)
        number_of_last_row_on_current_page = self.CSV_COUNT_ROWS_ON_PAGE
        count_rows = self.db.get_count_rows()
        index_of_current_row = None
        for index_of_current_row, row in enumerate(self.db.select_rows()):
            number_of_last_row_on_current_page = number_of_last_row_on_current_page - row[1] + 1
            if index_of_current_row >= number_of_last_row_on_current_page:
                exporter.close(is_last_page=index_of_current_row == count_rows - 1)
                number_of_last_row_on_current_page += self.CSV_COUNT_ROWS_ON_PAGE
                csv_current_page += 1
                exporter.open_new_page(csv_current_page)
                if progress_count_exported_files:
                    progress_count_exported_files(index_of_current_row + 1, count_rows, csv_current_page)

            exporter.write_row(row)
            number_of_last_row_on_current_page += row[1]

        if progress_count_exported_files and index_of_current_row is not None:
            progress_count_exported_files(index_of_current_row + 1, count_rows, csv_current_page)

        exporter.close(is_last_page=index_of_current_row is None or index_of_current_row == count_rows - 1)

        for row in self.db.select_all_tags():
            exporter.write_tag_row(*row)

        exporter.close_tags()

    def import_csv_to_db(self, csv_path):
        def process_file_status(*args):
            status, existed_path, inserted_path = self.get_file_status(*args)
            if args[2]:
                raise Exception(self.MESSAGE_DOUBLE_IMPORT.format(inserted_path, existed_path))

        for csv_filename in os.scandir(csv_path):
            with open(csv_filename.path, 'r', encoding='utf-8', newline='\n') as csv_file:
                for csv_row in csv.reader(csv_file):
                    self.db.append_row(tuple(csv_row))
                    if self.db.is_ready_for_insert():
                        self.db.insert_rows(func=process_file_status)

        self.db.insert_rows(func=process_file_status)

    def get_file_status(self, inserted_directory, inserted_filename, existed_directory, existed_filename):
        inserted_path = '{}/{}'.format(inserted_directory, inserted_filename)  # .removeprefix('/')
        inserted_path = inserted_path[1:] if inserted_path.startswith('/') else inserted_path
        if existed_directory is not None:
            existed_path = '{}/{}'.format(existed_directory, existed_filename)  # .removeprefix('/')
            existed_path = existed_path[1:] if existed_path.startswith('/') else existed_path
            is_replaced = inserted_directory != existed_directory
            is_renamed = inserted_filename != existed_filename
            is_exists = os.path.exists(existed_path)
            if is_replaced and not is_renamed:
                return STATUS_DUPLICATE if is_exists else STATUS_MOVED, existed_path, inserted_path
            elif not is_replaced and is_renamed:
                return STATUS_DUPLICATE if is_exists else STATUS_RENAMED, existed_path, inserted_path
            elif is_replaced and is_renamed:
                return STATUS_DUPLICATE if is_exists else STATUS_MOVED_AND_RENAMED, existed_path, inserted_path

            return STATUS_UNTOUCHED, existed_path, inserted_path

        return STATUS_NEW, None, inserted_path
