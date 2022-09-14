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

Требования к этой программе:
1. Независимо от того, какая некорректность допущена в заметке, обработка следующих заметок должна продолжаться.
    Ошибки в заметках допустимы.
2. Программа не должна изменять файлы заметок без ведома и согласия пользователя.
"""
import hashlib
import os
import re

import yaml

TEXT_PATH = 'D://Текст'
IGNORE_PATHS = [f'{TEXT_PATH}/.obsidian', f'{TEXT_PATH}/.trash']

IGNORE_PATHS = [os.path.normpath(path) for path in IGNORE_PATHS]
RE_URLS = r'https?://[a-zA-Z0-9-_./%]+'
re_urls = re.compile(RE_URLS)

ALLOWED_YAML_KEYS = {
    'tags': 'Хэштеги',
    'publicate_to': 'Публикация в сервисы',
    'birth_date': 'День рождения'
}


def get_string_hash(string):
    BLOCKSIZE = 65536
    hasher = hashlib.blake2s()
    bytes_of_string = string.encode('utf-8')
    for start_position in range(0, len(bytes_of_string), BLOCKSIZE):
        buf = bytes_of_string[start_position:start_position + BLOCKSIZE]
        hasher.update(buf)

    return hasher.hexdigest()


def publicate_to(service_name, data):
    service_data = data['publicate_to'][service_name]
    if service_name == 'syeysk':
        return {'id': 3456, 'url': 'https://syeysk.ru/blog/3456', 'publicate_datetime': '2022-09-12 23:10'}
    elif service_name == 'developsoc':
        return {'id': 'article_name', 'url': 'https://developsoc.ru/article_name', 'publicate_datetime': '2022-09-12 23:10'}
    elif service_name == 'knowledge':
        return {'id': 'article_name', 'url': 'https://github.com/article_name', 'publicate_datetime': '2022-09-12 23:10'}


def process_content(content, logger_action, action_data):
    content = content.strip()

    lines = content.split('\n')
    is_yaml = lines and lines[0] == '---'
    data_yaml = {}
    if is_yaml:
        yaml_length = 4
        for line in lines[1:]:
            if line == '---':
                break

            yaml_length += len(line) + 1

        data_yaml = yaml.load(content[:yaml_length], yaml.SafeLoader)
        content = content[yaml_length + 4:].rstrip()

    for key in data_yaml:
        if key not in ALLOWED_YAML_KEYS:
            action_data['key'] = key
            logger_action('unfound_yaml_key', action_data)

    title = ''
    if content.startswith('#'):
        title, content = content.split('\n', 1)
        content = content.rstrip()
        title = title.lstrip('# ')

    if not title:
        logger_action('unfound_title', action_data)

    publicate_to = data_yaml.get('publicate_to')
    if publicate_to:
        action_data['publicate_to'] = publicate_to
        action_data['body'] = content
        action_data['title'] = title
        action_data['current_hash'] = get_string_hash(content)
        for service_name, service_data in publicate_to.items():
            published_hash = service_data.get('published_hash')
            if published_hash is None:
                service_data['need_publicate'] = True
            elif published_hash != action_data['current_hash']:
                service_data['need_update'] = True

        logger_action('publicate_to', action_data)

    urls = re_urls.findall(content)
    for url in urls:
        action_data['url'] = url
        logger_action('found_url', action_data)


def scan_knowlege(logger_action):
    for dirpath, dirnames, filenames in os.walk(TEXT_PATH):
        if dirpath in IGNORE_PATHS:
            continue

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            action_data = {'filepath': filepath, 'relative_filepath': filepath[len(TEXT_PATH)+1:]}
            try:
                # Проверяем расширене файла: оно обязано быть в .md
                if not filename.endswith('.md'):
                    logger_action('invalid_extension', action_data)

                with open(filepath, 'r', encoding='utf-8') as file:
                    process_content(file.read(), logger_action=logger_action, action_data=action_data)
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
