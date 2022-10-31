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


KNOWLEDGE_OWNER = 'TVP-Support'
KNOWLEDGE_REPO = 'knowledge'
OWNER = 'shyzik93'
TOKEN = ''


class ServiceGithub(BaseService):
    """Имя форка должно соответствать оригиналу, форк должен быть прямым потомком оригинала"""
    url_template = 'https://api.github.com{}'
    SERVICE_NAME = 'knowledge_github'

    def __init__(self, **kwargs):
        super(ServiceGithub, self).__init__(**kwargs)
        self.knowledge_owner = KNOWLEDGE_OWNER
        self.knowledge_repo = KNOWLEDGE_REPO
        self.owner = OWNER
        self.branch = 'notes_from_extern_service'
        self.headers = {
            'accepts': 'application/vnd.github+json',
        }

    def get_url(self, url_path):
        return self.url_template.format(url_path)

    def has_fork(self):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}')
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            if data['fork']:
                parent = data['parent']
                if parent and parent['full_name'] == f'{self.knowledge_owner}/{self.knowledge_repo}':
                    return True

    def make_fork(self):
        url = self.get_url(f'/repos/{self.knowledge_owner}/{self.knowledge_repo}/forks')
        data = {'default_branch_only': True}
        response = requests.post(url, headers=self.headers, data=data, timeout=60*5)
        if response.status_code != 202:
            raise Exception('Error to make fork')

    def has_branch(self):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/branches/{self.branch}')
        response = requests.head(url, headers=self.headers)
        if response.status_code == 200:
            return True

    def get_last_commit_hash(self):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/commits')
        response = requests.get(url, params={'per_page': 1}, headers=self.headers)
        if response.status_code == 200:
            return response.json()[0]['sha']

        raise Exception('Error getting last commit\'s sh1')

    def make_branch(self, sha1):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/git/refs')
        data = {
            'ref': f'refs/heads/{self.branch}',
            'sha1': sha1,
        }
        response = requests.post(url, headers=self.headers, data=data)
        if response.status_code != 201:
            raise Exception('Error to make branch')

    def get_last_pull_request_id(self):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/pulls')
        params = {'per_page': 1, 'head': f'{self.owner}:{self.branch}', 'state': 'open'}
        response = requests.get(url, params=params, headers=self.headers)
        if response.status_code == 200:
            return response.json()[0]['id']

    def make_pull_request(self):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/pulls')
        data = {
            'title': 'The Pull Request from extern app',
            'head': f'{self.owner}:{self.branch}',
            'state': f'{self.knowledge_owner}:master',
        }
        response = requests.post(url, data=data, headers=self.headers)
        if response.status_code == 201:
            return response.json()['id']

        raise Exception('Error make Pull Request')

    def send_file(self, file_path, file_content, sha=None):
        url = self.get_url(f'/repos/{self.owner}/{self.knowledge_repo}/contents/{file_path}')
        data = {'branch': self.branch, 'message': '', 'content': file_content}
        if sha:
            data['sha'] = sha

        response = requests.put(url, data=data, headers=self.headers)
        if (sha and response.status_code == 200) or (not sha and response.status_code == 201):
            return True

        raise Exception('Error create or update file')

    def create_note(self):
        created = False
        if not self.has_fork():
            self.make_fork()
            created = True

        if created or not self.has_branch():
            sha1 = self.get_last_commit_hash()
            self.make_branch(sha1)
            created = True

        last_pull_requst_id = self.get_last_pull_request_id()
        if created or not last_pull_requst_id:
            self.make_pull_request()

        self.send_file(file_path=self.file_path, file_content=self.raw_content)
