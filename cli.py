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

subparser = parser.add_subparsers('scan')
subparser.add_argument('path', dest='path', action='store', require=True)
subparser.add_argument('struct', dest='struct', action='store', require=True)

subparser = parser.add_subparsers('makediff')
subparser.add_argument('path', dest='path', action='store', require=True)
subparser.add_argument('struct', dest='struct', action='store', require=True)
subparser.add_argument('diff', dest='diff', action='store', require=True)

subparser = parser.add_subparsers('applydiff')
subparser.add_argument('path', dest='path', action='store', require=True)
subparser.add_argument('diff', dest='diff', action='store', require=True)



