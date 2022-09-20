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
import datetime
import hashlib
import os
import re

from pykeepass import PyKeePass
import requests
import yaml

DEFAULT_PASSWORD_FILEPATH = os.path.normpath('D://Пароли.kdbx')
DEFAULT_NOTES_DIRPATH = os.path.normpath('D://Текст')
IGNORE_PATHS = [
    os.path.normpath(f'{DEFAULT_NOTES_DIRPATH}/.obsidian'),
    os.path.normpath(f'{DEFAULT_NOTES_DIRPATH}/.trash'),
]
RE_URLS = re.compile(r'https?://[a-zA-Z0-9А-Яа-яёЁ_./%?=-]+')
ALLOWED_YAML_KEYS = {
    'tags': 'Хэштеги',
    'publicate_to': 'В какие сервисы публиковать',
    'birth_date': 'Дата рождения',
    'death_date': 'Дата смерти',
}
DT_FORMAT = '%Y-%m-%d %H:%M:%S'


def get_string_hash(string):
    BLOCKSIZE = 65536
    hasher = hashlib.blake2s()
    bytes_of_string = string.encode('utf-8')
    for start_position in range(0, len(bytes_of_string), BLOCKSIZE):
        buf = bytes_of_string[start_position:start_position + BLOCKSIZE]
        hasher.update(buf)

    return hasher.hexdigest()


def get_password_data(
    service_name,
    group='main',
    app_name=True,
    password_filepath=DEFAULT_PASSWORD_FILEPATH,
    password='',
):
    pk = PyKeePass(password_filepath, password=password)
    title = f'{service_name}_{group}' if group else service_name
    if app_name:
        title = f'storage_scanner_{title}'
    password_data = pk.find_entries(title=title, first=True)
    print(password_data, dir(password_data))
    return password_data


class BaseService:
    SERVICE_NAME = None

    def __init__(self, title, body, password_filepath=DEFAULT_PASSWORD_FILEPATH, password=''):
        self.title = title
        self.body = body
        self._password_filepath = password_filepath
        self._password = password

    def get_password_data(self, group='main'):
        return get_password_data(
            self.SERVICE_NAME,
            group=group,
            password_filepath=self._password_filepath,
            password=self._password,
        )


class SyeyskService(BaseService):
    SERVICE_NAME = 'syeysk'

    def __init__(self, **kwargs):
        super(SyeyskService, self).__init__(**kwargs)

        self.url = 'https://syeysk.ru/api/blog/{method}'
        password_data = self.get_password_data()
        self.token = password_data.password
        self.headers = {'HTTP_AUTHORIZATION': f'Token {self.token}'}

    def create_note(self):
        data = {'title': self.title, 'content': self.body}
        response = requests.post(self.url.format(method='publicate'), data=data, headers=self.headers)
        response_data = response.json()
        if not response_data.get('success'):
            return {'error': response_data['error']}

        return {'id': response_data['id'], 'url': response_data['url']}

    def update_note(self, note_id):
        data = {'id': note_id, 'title': self.title, 'content': self.body}
        response = requests.post(self.url.format(method='update'), data=data, headers=self.headers)
        return {}


class DevelopsocService(BaseService):
    SERVICE_NAME = 'Developsoc'

    def __init__(self, **kwargs):
        super(DevelopsocService, self).__init__(**kwargs)

    def create_note(self):
        print('----', self._password)
        return {'id': 'article_name', 'url': 'https://developsoc.ru/article_name', 'publicate_datetime': '2022-09-12 23:10'}

    def update_note(self, note_id):
        return {}


class KnowledgeService(BaseService):
    SERVICE_NAME = 'knowledge'

    def __init__(self, **kwargs):
        super(KnowledgeService, self).__init__(**kwargs)

    def create_note(self):
        return {'id': 'article_name', 'url': 'https://github.com/article_name', 'publicate_datetime': '2022-09-12 23:10'}

    def update_note(self, note_id):
        print('----', self._password)
        return {}


class Note:
    """Класс, представлюящий заметку"""

    def __init__(self, meta, title, body, filepath):
        self.meta = meta
        self.title = title
        self.body = body
        self.filepath = filepath
        self.hash = get_string_hash('{}{}'.format(title, body))
        self.custom = {}

    def save(self):
        backup_filepath = '{}.backup'.format(self.filepath)
        with open(backup_filepath, 'w', encoding='utf-8') as file_note:
            yaml_str = yaml.dump(
                self.meta,
                Dumper=yaml.SafeDumper,
                explicit_start=True,
                explicit_end=False,
                sort_keys=False,
                allow_unicode=True,
                indent=4,
                width=70,
            )
            file_note.write('{}\n---\n\n'.format(yaml_str[:-2]))
            file_note.write('# {}\n\n'.format(self.title))
            file_note.write('{}\n'.format(self.body))

    def need_create_publication(self, service_name):
        """
        :param service_name: имя удалённого сервиса
        :return: "create" - если нужно создать заметку на удалённом сервисе, "update" - если нужно обновить,
         "nothing" - ничего не делать, так как заметка на удалённом сервисе находится в актуальном состоянии
        """
        publicate_to = self.meta.get('publicate_to')
        if publicate_to and service_name in publicate_to:
            service_data = publicate_to[service_name]
            published_hash = service_data.get('published_hash')
            if published_hash is None:
                return 'create'

            if published_hash != self.hash:
                return 'update'

        return 'nothing'

    def publicate(self, service_name, password_filepath=DEFAULT_PASSWORD_FILEPATH, password=''):
        publicate_to = self.meta.get('publicate_to')
        if publicate_to and service_name in publicate_to:
            service_data = publicate_to[service_name]
            if service_name == 'syeysk':
                service = SyeyskService(
                    title=self.title,
                    body=self.body,
                    password_filepath=password_filepath,
                    password=password
                )
            elif service_name == 'developsoc':
                service = DevelopsocService(
                    title=self.title,
                    body=self.body,
                    password_filepath=password_filepath,
                    password=password,
                )
            elif service_name == 'knowledge':
                service = KnowledgeService(
                    title=self.title,
                    body=self.body,
                    password_filepath=password_filepath,
                    password=password,
                )
            else:
                raise Exception('Unknown service: {}'.format(service_name))

            if self.need_create_publication(service_name) == 'create':
                response_data = service.create_note()
            elif self.need_create_publication(service_name) == 'update':
                response_data = service.update_note(service_data['id'])
            else:
                raise Exception('The note is already actual for service: {}'.format(service_name))

            service_data.update(response_data)
            service_data['published_hash'] = self.hash
            service_data['publicate_datetime'] = datetime.datetime.now().strftime(DT_FORMAT)
            return service_data


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
        content = content[yaml_length + 4:].lstrip()

    for key in data_yaml:
        if key not in ALLOWED_YAML_KEYS:
            action_data['key'] = key
            logger_action('unfound_yaml_key', action_data)

    title = ''
    if content.startswith('# '):
        parts = content.split('\n', 1)
        title, content = parts if len(parts) == 2 else (parts[0], '')
        content = content.lstrip()
        title = title.lstrip('#')
        title = title.strip()

    if not title:
        logger_action('unfound_title', action_data)

    if data_yaml.get('publicate_to'):
        note = Note(data_yaml, title, content, action_data['filepath'])
        action_data['note'] = note
        logger_action('publicate_to', action_data)

    urls = RE_URLS.findall(content)
    for url in urls:
        action_data['url'] = url
        logger_action('found_url', action_data)


def scan_knowlege(logger_action, notes_dirpath):
    for dirpath, dirnames, filenames in os.walk(notes_dirpath):
        if dirpath in IGNORE_PATHS:
            continue

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            action_data = {'filepath': filepath, 'relative_filepath': filepath[len(notes_dirpath)+1:]}
            try:
                # Проверяем расширене файла: оно обязано быть в .md
                if not filename.endswith('.md'):
                    logger_action('invalid_extension', action_data)

                with open(filepath, 'r', encoding='utf-8') as file:
                    process_content(file.read(), logger_action, action_data)
            except Exception as error:
                print(filepath)
                raise error


if __name__ == '__main__':
    def logger_action(name, data):
        if name == 'invalid_extension':
            print('Invalid files\'s extension:', data)
        else:
            print(name, data)

    scan_knowlege(logger_action, DEFAULT_NOTES_DIRPATH)
