"""
1. Проверять наличие бэкапов репозиториев. Делать бэкапы, если их нет.
2. Проверять наличие локальных версий: вебстраниц, видео с ютюба, таблиц и документов с гугл-докс, облачных хранилищ (яндекс-диска, мэйлру, гугл-диск). Скачивать страницу или видео, если их нет локально. Соответствия "ссылка-файл" сохранять в текстовый файл, начинающийся с имени "авто_". На экран выводить недоступные ссылки, скачанные файлы.
3. Проверять доступность файлов по локальной ссылке.

В каталогизаторе:
- вместо csv генерировать файлы md, содержащие таблицы.
- создавать файлы "книга_{hash}.md" в отдельном каталоге.
Таким образом база-файлы каталогизатора будут подчинены общим правилам Обсидиана.

## Правила

Имя файла:
- расширение: .md
- имя: [0-9a-zа-я_]
- дата в начале имени файла пишется в формате YY-mm-dd-

Содержимое:
- кодировка: utf-8
- доступные протоколы URL: https://, http://
"""

import os
import re

TEXT_PATH = 'D://Текст'
IGNORE_PATHS = [f'{TEXT_PATH}/.obsidian', f'{TEXT_PATH}/.trash']

IGNORE_PATHS = [os.path.normpath(path) for path in IGNORE_PATHS]
RE_URLS = r'https?://[a-zA-Z0-9-_./%]+'
re_urls = re.compile(RE_URLS)


def process_file(text, logger_action):
    urls = re_urls.findall(text)
    for url in urls:
        logger_action('found_url', {'url': url})


def scan_knowlege(logger_action):
    for dirpath, dirnames, filenames in os.walk(TEXT_PATH):
        if dirpath in IGNORE_PATHS:
            continue

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                # Проверяем расширене файла: оно обязано быть в .md
                if not filename.endswith('.md'):
                    logger_action('invalid_extension', {'filepath': filepath})

                filepath = os.path.join(dirpath, filename)
                with open(filepath, 'r', encoding='utf-8') as file:
                    process_file(file.read(), logger_action=logger_action)
            except Exception as error:
                print(filepath)
                raise error


if __name__ == '__main__':
    def logger_action(name, data):
        if name == 'invalid_extension':
            print('Invalid files\'s extension:', data)
        else:
            print(name, data)

    scan_knowlege(logger_action=logger_action)
