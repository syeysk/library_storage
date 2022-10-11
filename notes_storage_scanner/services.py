import requests
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError

from constants_paths import DEFAULT_PASSWORD_FILEPATH


def get_password_data(
    service_name,
    group='main',
    app_name=True,
    password_filepath=DEFAULT_PASSWORD_FILEPATH,
    password='',
):
    try:
        pk = PyKeePass(password_filepath, password=password)
    except CredentialsError as error:
        print('Invalid password:', error)
        raise Exception from error

    title = f'{service_name}_{group}' if group else service_name
    if app_name:
        title = f'storage_scanner_{title}'
    password_data = pk.find_entries(title=title, first=True)
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

        self.url = 'https://syeysk.ru/api/blog/{method}/'
        password_data = self.get_password_data()
        self.token = password_data.password
        self.headers = {'HTTP_AUTHORIZATION': f'Token {self.token}'}

        parts = self.body.split('\n', 1)
        self.cut = parts[0] if parts else ''
        self.body = parts[1] if len(parts) > 1else self.cut

    def create_note(self):
        data = {'title': self.title, 'content': self.body, 'cut': self.cut}
        response = requests.post(self.url.format(method='create_article'), json=data, headers=self.headers)
        if response.status_code == 200:
            response_data = response.json()
            return True, {'id': response_data['id'], 'url': response_data['url']}

        return False, response.text

    def update_note(self, note_id):
        data = {'article_id': note_id, 'title': self.title, 'content': self.body, 'cut': self.cut}
        response = requests.post(self.url.format(method='update_article'), json=data, headers=self.headers)
        if response.status_code == 200:
            response_data = response.json()
            return True, {'url': response_data['url']}

        return False, response.text


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