import os
import csv
from urllib.parse import quote


class CSVExporter:
    def __init__(self, storage_structure, storage_directory):
        self.csv_writer = None
        self.csv_file = None
        self.storage_structure = storage_structure
        if not os.path.exists(self.storage_structure):
            os.makedirs(self.storage_structure, exist_ok=True)

    def open_new_page(self, current_page):
        csv_full_path = os.path.join(self.storage_structure, '{}.csv'.format(str(current_page)))
        self.csv_file = open(csv_full_path, 'w', encoding='utf-8', newline='\n')
        self.csv_writer = csv.writer(self.csv_file)

    def write_row(self, row):
        self.csv_writer.writerow(row)

    def close(self, is_last_page):
        if self.csv_file:
            self.csv_file.close()


class MarkdownExporter:
    TABLE_HEADER = (
        '# Список книг из локального хранилища\n\n'
        'ID | Ссылка на описание | Ссылка на книгу\n'
        '--- | --- | ---\n'
    )
    TABLE_ROW = '{id} | [{hash}](книга_{id}) | [{name}](file://{relative_storage_pathdir}{pathdir}/{filename})\n'
    PREV_PAGE = '[<< Предыдщая страница](список_книг_{})'
    NEXT_PAGE = '[Следующая страница >>](список_книг_{})'

    TAGS_TABLE_HEADER = (
        '# Список тегов\n\n'
        'ID | Имя тега | Родительский тег\n'
        '--- | --- | ---\n'
    )
    TAG_TABLE_ROW = '{tag_id} | {name} | {parent_id}\n'

    def __init__(self, storage_structure, storage_directory):
        self.storage_structure = storage_structure
        self.csv_file = None
        self.current_page = None
        self.storage_directory = storage_directory
        if not os.path.exists(self.storage_structure):
            os.makedirs(self.storage_structure, exist_ok=True)

        self.tags_file = open(os.path.join(self.storage_structure, 'теги.md'), 'w', encoding='utf-8')
        self.tags_file.write(self.TAGS_TABLE_HEADER)

    def open_new_page(self, current_page):
        csv_full_path = os.path.join(self.storage_structure, 'список_книг_{}.md'.format(str(current_page)))
        self.csv_file = open(csv_full_path, 'w', encoding='utf-8')
        self.csv_file.write(self.TABLE_HEADER)
        self.current_page = current_page

    def write_row(self, row):
        # disk_one = self.storage_directory.split('://', 1)[0]
        # disk_two = self.storage_structure.split('://', 1)[0]
        relpath = os.path.relpath(self.storage_directory, self.storage_structure).replace('\\', '/')
        self.csv_file.write(
            self.TABLE_ROW.format(
                id=row[1],
                hash=row[0],
                name=row[3].replace('[', '').replace(']', '').replace('(', '').replace(')', ''),
                relative_storage_pathdir=relpath,
                pathdir=quote('/{}'.format(row[2])) if row[2] else '',
                filename=quote(row[3]),
            )
        )
    
    def write_tag_row(self, tag_id, name, parent_tag_id):
        if parent_tag_id is None:
            parent_tag_id = ''

        self.tags_file.write(self.TAG_TABLE_ROW.format(tag_id=tag_id, name=name, parent_id=parent_tag_id))

    def close_tags(self):
        self.tags_file.close()

    def close(self, is_last_page):
        prev_page = self.PREV_PAGE.format(self.current_page - 1) if self.current_page > 1 else ''
        next_page = self.NEXT_PAGE.format(self.current_page + 1) if not is_last_page else ''
        self.csv_file.write(f'\n{prev_page} | {self.current_page} | {next_page}\n--- | --- | ---\n')

        if self.csv_file:
            self.csv_file.close()
