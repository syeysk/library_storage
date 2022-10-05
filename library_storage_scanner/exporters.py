import os
import csv


class CSVExporter:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.csv_writer = None
        self.csv_file = None

    def open_new_page(self, csv_current_page):
        csv_full_path = os.path.join(self.csv_path, '{}.csv'.format(str(csv_current_page)))
        self.csv_file = open(csv_full_path, 'w', encoding='utf-8', newline='\n')
        self.csv_writer = csv.writer(self.csv_file)

    def write_row(self, row):
        self.csv_writer.writerow(row)

    def close(self):
        self.csv_file.close()


class MarkdownExporter:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.csv_file = None

    def open_new_page(self, csv_current_page):
        TABLE_HOLDER = 'Описание | Ссылка на книгу\n--- | ---\n'
        csv_full_path = os.path.join(self.csv_path, '{}.md'.format(str(csv_current_page)))
        self.csv_file = open(csv_full_path, 'w', encoding='utf-8')
        self.csv_file.write(TABLE_HOLDER)

    def write_row(self, row):
        TABLE_ROW = '[{id}](книга_{id}) | [{name}](D://Книги/{name}/{pathdir})\n'
        self.csv_file.write(TABLE_ROW.format(id=row[1], name=row[3], pathdir=row[2]))

    def close(self):
        self.csv_file.close()
