"""
Основные команды:
- `syeysk-stor scan --path --struct`  — сканирует оригинальную директорию --path, генерирует архив --struct со структурой директории.
- `syeysk-stor makediff --path --struct --diff` — сканирует копию директории --path и создаёт diff-файл --diff относительно структуры --struct оригинальной директории
- `syeysk-stor applydiff --path --diff` — применяет diff-файл --diff к оригинальной директории --path

Опции для `libstor`:
- `--delete-dubbles` - удалять с диска файл, если его хеш совпадает с уже имеющимся в базе файлом, при этом их имена отличаются. Иначе — выбрасывает исключение
- `--config` - путь к конфигу. Если указан, то значения недостающих опций будут браться из данного конфига.
"""
import argparse
#import os

from src.config import config
from src.scanner import DBStorage, LibraryStorage

#DEFAULT_DB_PATH = os.path.expandvars(os.path.join('%TEMP%', 'cli_library_storage.db'))

parser = argparse.ArgumentParser(description='Каталогизатор')
#parser.add_argument(
#    '--db',
#    dest='db',
#    action='store',
#    required=False,
#    help='original storage',
#    default=DEFAULT_DB_PATH
#)

subparser = parser.add_subparsers(dest='command')

#parser_scan = subparser.add_parser('scan')
#parser_scan.add_argument('--path', dest='path', action='store', required=True, help='original storage')

#parser_scan = subparser.add_parser('import')
#parser_scan.add_argument('--struct', dest='struct', action='store', required=True)

#parser_scan = subparser.add_parser('export')
#parser_scan.add_argument('--struct', dest='struct', action='store', required=True)

#parser_makediff = subparser.add_parser('makediff')
#parser_makediff.add_argument('--path', dest='path', action='store', required=True, help='changed storage')
#parser_makediff.add_argument('--diff', dest='diff', action='store', required=True)

#parser_applydiff = subparser.add_parser('applydiff')
#parser_applydiff.add_argument('--path', dest='path', action='store', required=True, help='original storage')
#parser_applydiff.add_argument('--diff', dest='diff', action='store', required=True, help='diff from changed storage')

parser_tag = subparser.add_parser('tag', help='Command to manage the tags')
parser_tag.add_argument('tag_id', nargs='?', help='tag id', default=None)

parser_tag_add = subparser.add_parser('tagadd', help='Command to add a tag')
parser_tag_add.add_argument('--parent_id', '-p', nargs='?', help='parent tag id', default=None)
parser_tag_add.add_argument('name', nargs='*', help='tag name')

args = parser.parse_args()
#db_path = os.path.abspath(args.db) if args.db != ':temp:' else args.path
#if args.command == 'scan':
#    library_dir = os.path.abspath(args.path)
#    with LibraryStorage(db_path=db_path) as lib_storage:
#        lib_storage.scan_to_db(library_path=library_dir)

#elif args.command == 'import':
#    struct_dir = os.path.abspath(args.struct)
#    with LibraryStorage(db_path=db_path) as lib_storage:
#        lib_storage.import_csv_to_db(struct_dir)

#elif args.command == 'export':
#    struct_dir = os.path.abspath(args.struct)
#    with LibraryStorage(db_path=db_path) as lib_storage:
#        lib_storage.export_db(struct_dir)

#elif args.command == 'makediff':
#    library_dir = os.path.abspath(args.path)
#    diff_filepath = os.path.abspath(args.diff)
#    with LibraryStorage(db_path=db_path) as lib_storage:
#        lib_storage.scan_to_db(library_path=library_dir)
#        lib_storage.save_diff(library_path=library_dir, diff_file_path=diff_filepath)

#elif args.command == 'applydiff':
#    library_dir = os.path.abspath(args.path)
#    diff_filepath = os.path.abspath(args.diff)
#    with LibraryStorage(db_path=db_path) as lib_storage:
#        lib_storage.apply_diff(diff_filepath)

with LibraryStorage() as lib_storage:
    lib_storage.set_db(DBStorage(config.db_path))

    if args.command == 'tag' and args.tag_id:
        tag_name, parent_id = lib_storage.db.select_tag(args.tag_id)
        print('Имя:', tag_name, '\nРодитель:', parent_id if parent_id else 'нет')

    elif args.command == 'tag':
        def print_row(tag_id, tag_name, parent_id):
            if parent_id is None:
                parent_id = ''

            print(str(tag_id).center(5), '|', tag_name.ljust(20), '|', str(parent_id).center(5))

        print('-'*38)
        print_row('ID', 'Имя тега', 'Родитель')
        print('-'*38)
        for tag_id, tag_name, parent_id in lib_storage.db.select_all_tags():
            print_row(tag_id, tag_name, parent_id)

        print('-'*38)

    elif args.command == 'tagadd':
        tag_id = lib_storage.db.insert_tag(' '.join(args.name), args.parent_id)
        print('ID добавленного тега:', tag_id)
