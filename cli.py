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

parser = argparse.ArgumentParser(description='Система поддержания целостности копий директорий')

subparser = parser.add_subparsers(dest='command')

parser_scan = subparser.add_parser('scan')
parser_scan.add_argument('--path', dest='path', action='store', required=True)
parser_scan.add_argument('--struct', dest='struct', action='store', required=True)

parser_makediff = subparser.add_parser('makediff')
parser_makediff.add_argument('--path', dest='path', action='store', required=True)
parser_makediff.add_argument('--struct', dest='struct', action='store', required=True)
parser_makediff.add_argument('--diff', dest='diff', action='store', required=True)

parser_applydiff = subparser.add_parser('applydiff')
parser_applydiff.add_argument('--path', dest='path', action='store', required=True)
parser_applydiff.add_argument('--diff', dest='diff', action='store', required=True)

args = parser.parse_args()
if args.command == 'scan':
    ...
elif args.command == 'makediff':
    ...
elif args.command == 'applydiff':
    ...
